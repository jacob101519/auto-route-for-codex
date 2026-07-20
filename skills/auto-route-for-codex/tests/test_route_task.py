from __future__ import annotations

import copy
import itertools
import json
import os
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "scripts" if (ROOT / "scripts" / "route_task.py").is_file() else ROOT
sys.path.insert(0, str(SOURCE_PATH))
from route_task import REQUIRED_HOST_CAPABILITIES, canonical_sha256, recommend  # noqa: E402


FIXTURES = Path(__file__).parent / "fixtures" / "cases.json"


def fresh(value: dict) -> dict:
    value = copy.deepcopy(value)
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if value["current"]["evidence_status"] == "verified":
        value["current"]["observed_at"] = observed_at
        value["current_provenance"].update(observed_at=observed_at, ttl_seconds=600)
        value["current_provenance"]["content_sha256"] = canonical_sha256({
            "model": value["current"]["model"],
            "effort": value["current"]["effort"],
            "observed_at": observed_at,
        })
    value["catalog_provenance"].update(observed_at=observed_at, ttl_seconds=604800)
    value["catalog_provenance"]["content_sha256"] = canonical_sha256({
        "role_models": value["host_role_models"],
        "observed_at": observed_at,
    })
    value["host_provenance"].update(observed_at=observed_at, ttl_seconds=600)
    value["host_provenance"]["content_sha256"] = canonical_sha256({
        "surface": value["host_surface"],
        "capabilities": value["host_capabilities"],
        "models": sorted(value["host_models"]),
        "thinking": sorted(value["host_thinking"]),
        "role_models": value["host_role_models"],
        "observed_at": observed_at,
    })
    return value


def cases() -> list[dict]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


class PublicRouterTests(unittest.TestCase):
    def test_fixtures_are_deterministic_and_match_locked_routes(self) -> None:
        for case in cases():
            with self.subTest(case=case["name"]):
                payload = fresh(case["input"])
                first = recommend(payload)
                second = recommend(payload)
                self.assertEqual(first, second)
                expected = case["expected"]
                for field in ("model_role", "model", "thinking", "topology", "resolution"):
                    self.assertEqual(first["recommended"][field], expected[field])
                self.assertEqual(first["status"], expected["status"])
                for field in ("action", "benefit", "transfer", "source_disposition"):
                    self.assertEqual(first["decision"][field], expected[field])
                if first["recommended"]["resolution"] == "resolved":
                    self.assertEqual(first["tool_overrides"], {
                        "model": first["recommended"]["model"],
                        "thinking": first["recommended"]["thinking"],
                    })
                else:
                    self.assertIsNone(first["tool_overrides"])

    def test_only_four_decision_combinations_are_reachable(self) -> None:
        legal = {
            ("stay", "none", "none", "keep"),
            ("stay", "efficiency", "none", "keep"),
            ("reroute", "quality", "fork", "archive_after_continuation_ready"),
            ("reroute", "parallelism", "fork", "archive_after_continuation_ready"),
        }
        observed = set()
        for case in cases():
            decision = recommend(fresh(case["input"]))["decision"]
            observed.add(tuple(decision[field] for field in ("action", "benefit", "transfer", "source_disposition")))
        self.assertTrue(observed.issubset(legal))
        self.assertEqual(observed, legal)

    def test_each_missing_host_tool_blocks_quality_fork(self) -> None:
        base = cases()[0]["input"]
        for capability in REQUIRED_HOST_CAPABILITIES:
            with self.subTest(capability=capability):
                payload = copy.deepcopy(base)
                payload["host_capabilities"][capability] = False
                result = recommend(fresh(payload))
                self.assertEqual(
                    tuple(result["decision"][field] for field in ("action", "benefit", "transfer", "source_disposition")),
                    ("stay", "none", "none", "keep"),
                )
                self.assertEqual(result["decision"]["reason_code"], "host_capability_gate_not_satisfied")
                self.assertFalse(result["evidence"]["continuation_capable"])

    def test_non_desktop_surface_blocks_fork(self) -> None:
        for surface in ("codex_cli", "codex_ide", "codex_cloud", "unknown"):
            with self.subTest(surface=surface):
                payload = copy.deepcopy(cases()[0]["input"])
                payload["host_surface"] = surface
                result = recommend(fresh(payload))
                self.assertEqual((result["decision"]["action"], result["decision"]["transfer"]), ("stay", "none"))
                self.assertEqual(result["decision"]["reason_code"], "host_capability_gate_not_satisfied")

    def test_parallel_shape_and_delegation_are_separate_gates(self) -> None:
        payload = copy.deepcopy(cases()[2]["input"])
        authorized = recommend(fresh(payload))
        self.assertEqual(authorized["recommended"]["topology"], "parallel")
        self.assertEqual(
            tuple(authorized["decision"][field] for field in ("action", "benefit", "transfer", "source_disposition")),
            ("reroute", "parallelism", "fork", "archive_after_continuation_ready"),
        )

        payload["profile"]["parallelism_observed"] = False
        authorization_only = recommend(fresh(payload))
        self.assertEqual(authorization_only["recommended"]["topology"], "parallel")
        self.assertEqual(
            tuple(authorization_only["decision"][field] for field in ("action", "benefit", "transfer", "source_disposition")),
            ("stay", "none", "none", "keep"),
        )
        self.assertEqual(authorization_only["decision"]["reason_code"], "parallelism_not_observed")

    def test_observed_parallelism_does_not_replace_delegation_authority(self) -> None:
        payload = copy.deepcopy(cases()[2]["input"])
        payload["profile"]["parallelism_observed"] = True
        payload["profile"]["delegation_authorized"] = False
        result = recommend(fresh(payload))
        self.assertEqual(result["recommended"]["topology"], "parallel")
        self.assertEqual(
            tuple(result["decision"][field] for field in ("action", "benefit", "transfer", "source_disposition")),
            ("stay", "none", "none", "keep"),
        )
        self.assertEqual(result["decision"]["reason_code"], "delegation_not_authorized")

    def test_stale_future_tampered_or_duplicate_provenance_cannot_fork(self) -> None:
        base = fresh(cases()[0]["input"])
        variants = []
        stale = copy.deepcopy(base)
        stale["host_provenance"].update(observed_at="2000-01-01T00:00:00Z", ttl_seconds=1)
        variants.append(stale)
        future = copy.deepcopy(base)
        future["host_provenance"]["observed_at"] = "2999-01-01T00:00:00Z"
        variants.append(future)
        tampered = copy.deepcopy(base)
        tampered["host_provenance"]["content_sha256"] = "0" * 64
        variants.append(tampered)
        duplicate = copy.deepcopy(base)
        duplicate["host_provenance"]["receipt_id"] = duplicate["catalog_provenance"]["receipt_id"]
        variants.append(duplicate)
        missing_current = copy.deepcopy(base)
        missing_current["current_provenance"] = None
        variants.append(missing_current)
        for index, payload in enumerate(variants):
            with self.subTest(index=index):
                result = recommend(payload)
                self.assertEqual((result["decision"]["action"], result["decision"]["transfer"]), ("stay", "none"))
                self.assertNotEqual(result["decision"]["evidence_status"], "verified")

    def test_privacy_bounded_session_setting_provenance_is_supported(self) -> None:
        payload = fresh(cases()[0]["input"])
        payload["current_provenance"]["source"] = "local_session_turn_context"
        result = recommend(payload)
        self.assertEqual(result["evidence"]["current"], {
            "status": "verified",
            "provenance": "session_turn_context_receipt",
        })
        self.assertEqual(result["decision"]["transfer"], "fork")

    def test_strict_input_contract_and_profile_types(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_input_contract"):
            recommend({"schema_version": "1.0", "current": {}, "extra": True})
        base = fresh(cases()[0]["input"])
        variants = []
        missing = copy.deepcopy(base)
        missing["profile"].pop("scope")
        variants.append(missing)
        extra = copy.deepcopy(base)
        extra["profile"]["task_text"] = "forbidden"
        variants.append(extra)
        bool_count = copy.deepcopy(base)
        bool_count["profile"]["parallel_workstreams"] = True
        variants.append(bool_count)
        for payload in variants:
            with self.assertRaisesRegex(ValueError, "invalid_profile"):
                recommend(payload)

    def test_output_is_minimal_private_and_authorization_bound(self) -> None:
        result = recommend(fresh(cases()[0]["input"]))
        self.assertEqual(set(result), {
            "schema_version", "status", "decision", "current", "recommended",
            "tool_overrides", "evidence", "route_authorization",
            "effective_task_kind", "reason_codes",
        })
        self.assertRegex(result["route_authorization"], r"^[0-9a-f]{64}$")
        rendered = json.dumps(result).lower()
        for forbidden in ("user_text", "task_text", "thread_id", "/users/", "cookie", "credential", "token"):
            self.assertNotIn(forbidden, rendered)

    def test_contract_validator_passes(self) -> None:
        script = ROOT / "scripts/validate_contracts.py" if (ROOT / "scripts/validate_contracts.py").is_file() else ROOT / "validate_contracts.py"
        completed = subprocess.run([sys.executable, str(script)], check=False, capture_output=True, text=True)
        self.assertEqual((completed.returncode, completed.stderr), (0, ""), completed.stdout + completed.stderr)
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["status"], "pass")
        self.assertEqual(summary["schemas"], 4)
        self.assertEqual(summary["instances"], len(cases()))
        self.assertGreaterEqual(summary["semantic_negative_instances"], 8)


if __name__ == "__main__":
    unittest.main()
