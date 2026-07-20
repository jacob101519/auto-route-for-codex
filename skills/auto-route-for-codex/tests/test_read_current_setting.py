from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" if (ROOT / "scripts" / "read_current_setting.py").is_file() else ROOT
SCRIPT = SCRIPTS / "read_current_setting.py"
SPEC = importlib.util.spec_from_file_location("public_read_current_setting", SCRIPT)
assert SPEC and SPEC.loader
reader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reader)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def turn_context(model: object, effort: object, observed_at: object) -> dict[str, object]:
    return {
        "timestamp": observed_at,
        "type": "turn_context",
        "payload": {"model": model, "effort": effort},
    }


class ReadCurrentSettingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.codex_home = Path(self.temporary.name)
        self.thread_id = str(uuid.uuid4())
        self.other_thread_id = str(uuid.uuid4())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_session(
        self,
        thread_id: str,
        records: list[dict[str, object] | str],
        date_path: str = "2026/07/19",
        meta_id: str | None = None,
    ) -> Path:
        directory = self.codex_home / "sessions" / date_path
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"rollout-synthetic-{thread_id}.jsonl"
        values: list[dict[str, object] | str] = [
            {"type": "session_meta", "payload": {"id": meta_id or thread_id}},
            *records,
        ]
        with path.open("w", encoding="utf-8") as handle:
            for value in values:
                handle.write(value if isinstance(value, str) else json.dumps(value))
                handle.write("\n")
        return path

    def run_reader(self, thread_id: str | None = None) -> tuple[int, dict, str]:
        environment = os.environ.copy()
        environment["CODEX_HOME"] = str(self.codex_home)
        selected = self.thread_id if thread_id is None else thread_id
        if selected == "MISSING":
            environment.pop("CODEX_THREAD_ID", None)
        else:
            environment["CODEX_THREAD_ID"] = selected
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
            timeout=5,
        )
        return completed.returncode, json.loads(completed.stdout), completed.stderr

    def test_reads_latest_exact_setting_and_emits_router_provenance(self) -> None:
        older = timestamp()
        latest = timestamp()
        self.write_session(self.other_thread_id, [turn_context("other-model", "medium", latest)])
        self.write_session(self.thread_id, [
            turn_context("model-deep", "max", older),
            turn_context("model-deep", "high", latest),
        ])
        code, result, stderr = self.run_reader()
        self.assertEqual((code, stderr, result["status"]), (0, "", "verified"))
        current = result["current"]
        provenance = result["current_provenance"]
        self.assertEqual(
            current,
            {
                "evidence_status": "verified",
                "model": "model-deep",
                "effort": "high",
                "observed_at": latest,
            },
        )
        encoded = json.dumps(
            {"model": "model-deep", "effort": "high", "observed_at": latest},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(provenance["content_sha256"], hashlib.sha256(encoded).hexdigest())
        self.assertEqual(provenance["source"], "local_session_turn_context")

    def test_unknown_results_are_exit_zero_and_privacy_bounded(self) -> None:
        for selected, reason in (
            ("MISSING", "missing_thread_id"),
            ("../bad", "invalid_thread_id"),
            (self.thread_id.upper(), "invalid_thread_id"),
            (self.thread_id, "unsafe_session_root"),
        ):
            with self.subTest(reason=reason):
                code, result, stderr = self.run_reader(selected)
                self.assertEqual((code, stderr), (0, ""))
                self.assertEqual(result, {"status": "unknown", "reason": reason})

    def test_session_meta_must_match_and_be_unambiguous(self) -> None:
        now = timestamp()
        self.write_session(self.thread_id, [turn_context("model-deep", "high", now)], meta_id=self.other_thread_id)
        self.assertEqual(self.run_reader()[1]["reason"], "session_meta_mismatch")
        self.codex_home.joinpath("sessions").rename(self.codex_home / "old-sessions")
        self.write_session(self.thread_id, [turn_context("model-deep", "high", now)], "2026/07/18")
        self.write_session(self.thread_id, [turn_context("model-deep", "high", now)], "2026/07/19")
        self.assertEqual(self.run_reader()[1]["reason"], "ambiguous_session")

    def test_latest_invalid_setting_does_not_fall_back(self) -> None:
        now = timestamp()
        self.write_session(self.thread_id, [
            turn_context("model-deep", "high", now),
            turn_context("bad model", "high", now),
        ])
        self.assertEqual(self.run_reader()[1]["reason"], "invalid_latest_setting")

    def test_incomplete_tail_is_ignored_but_complete_corruption_fails_closed(self) -> None:
        now = timestamp()
        path = self.write_session(self.thread_id, [turn_context("model-deep", "xhigh", now)])
        with path.open("ab") as handle:
            handle.write(b'{"type":"turn_context"')
        self.assertEqual(self.run_reader()[1]["current"]["effort"], "xhigh")
        with path.open("ab") as handle:
            handle.write(b"\n{malformed}\n")
        self.assertEqual(self.run_reader()[1]["reason"], "corrupt_record_after_setting")

    def test_symlink_and_group_writable_session_files_are_rejected(self) -> None:
        now = timestamp()
        target = self.write_session(self.other_thread_id, [turn_context("model-deep", "high", now)])
        link = target.parent / f"rollout-synthetic-{self.thread_id}.jsonl"
        link.symlink_to(target)
        self.assertEqual(self.run_reader()[1]["reason"], "unsafe_session_file")
        link.unlink()
        path = self.write_session(self.thread_id, [turn_context("model-deep", "high", now)])
        path.chmod(0o664)
        self.assertEqual(self.run_reader()[1]["reason"], "unsafe_session_file")

    def test_output_does_not_expose_session_content_or_identifiers(self) -> None:
        now = timestamp()
        record = turn_context("model-deep", "high", now)
        record["payload"]["credential"] = "synthetic-private-value"
        self.write_session(self.thread_id, [
            {"type": "user_message", "payload": {"text": "private-task-text"}},
            record,
        ])
        _, result, stderr = self.run_reader()
        rendered = json.dumps(result)
        self.assertEqual(stderr, "")
        for forbidden in (
            "synthetic-private-value",
            "private-task-text",
            self.thread_id,
            str(self.codex_home),
        ):
            self.assertNotIn(forbidden, rendered)

    def test_reader_enforces_monotonic_budget(self) -> None:
        with self.assertRaises(TimeoutError):
            reader.complete_lines(b"{}\n", False, True, 0.0)


if __name__ == "__main__":
    unittest.main()
