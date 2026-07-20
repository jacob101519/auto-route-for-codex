#!/usr/bin/env python3
"""Read the current Codex setting through a bounded local fallback."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


THREAD_ID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
MAX_HEAD_BYTES = 1024 * 1024
MAX_TAIL_BYTES = 16 * 1024 * 1024
MAX_TAIL_LINES = 8192
MAX_CANDIDATES = 4096
TIME_BUDGET_SECONDS = 1.0
PROVENANCE_TTL_SECONDS = 600


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    return 0


def unknown(reason: str) -> int:
    return emit({"status": "unknown", "reason": reason})


def check_budget(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise TimeoutError


def secure_directory(path: Path, uid: int) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISDIR(info.st_mode)
        and not stat.S_ISLNK(info.st_mode)
        and info.st_uid == uid
        and not info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    )


def iter_candidates(
    codex_home: Path,
    thread_id: str,
    deadline: float,
) -> tuple[list[Path], str | None]:
    uid = os.getuid()
    sessions_root = codex_home / "sessions"
    if not secure_directory(codex_home, uid) or not secure_directory(sessions_root, uid):
        return [], "unsafe_session_root"
    try:
        canonical_root = sessions_root.resolve(strict=True)
    except OSError:
        return [], "unsafe_session_root"
    suffix = f"-{thread_id}.jsonl"
    matches: list[Path] = []
    seen = 0
    try:
        for year in sessions_root.iterdir():
            check_budget(deadline)
            if not secure_directory(year, uid):
                return [], "unsafe_session_tree"
            for month in year.iterdir():
                check_budget(deadline)
                if not secure_directory(month, uid):
                    return [], "unsafe_session_tree"
                for day in month.iterdir():
                    check_budget(deadline)
                    if not secure_directory(day, uid):
                        return [], "unsafe_session_tree"
                    if canonical_root not in day.resolve(strict=True).parents:
                        return [], "unsafe_session_tree"
                    for candidate in day.iterdir():
                        check_budget(deadline)
                        seen += 1
                        if seen > MAX_CANDIDATES:
                            return [], "candidate_limit_exceeded"
                        if candidate.name.startswith("rollout-") and candidate.name.endswith(suffix):
                            matches.append(candidate)
    except TimeoutError:
        return [], "time_budget_exceeded"
    except OSError:
        return [], "session_unreadable"
    if not matches:
        return [], "session_not_found"
    return sorted(matches), None


def secure_open(path: Path) -> tuple[int | None, os.stat_result | None, str | None]:
    uid = os.getuid()
    try:
        if not hasattr(os, "O_NOFOLLOW"):
            return None, None, "nofollow_unavailable"
        before = path.lstat()
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_ISLNK(before.st_mode)
            or before.st_uid != uid
            or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or before.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            or before.st_nlink != 1
        ):
            return None, None, "unsafe_session_file"
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
        fd = os.open(path, flags)
        after = os.fstat(fd)
        if (
            (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
            or not stat.S_ISREG(after.st_mode)
            or after.st_uid != uid
            or after.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or after.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            or after.st_nlink != 1
            or after.st_size > MAX_FILE_SIZE
        ):
            os.close(fd)
            return None, None, "unsafe_session_file"
        return fd, after, None
    except OSError:
        return None, None, "session_unreadable"


def complete_lines(
    data: bytes,
    discard_first: bool,
    require_final_newline: bool,
    deadline: float,
) -> list[bytes]:
    check_budget(deadline)
    if discard_first:
        split = data.find(b"\n")
        data = b"" if split < 0 else data[split + 1 :]
    lines = data.splitlines(keepends=True)
    check_budget(deadline)
    if require_final_newline and data and not data.endswith(b"\n") and lines:
        lines.pop()
    return [line[:-1] if line.endswith(b"\n") else line for line in lines]


def exact_session_meta(fd: int, thread_id: str, deadline: float) -> bool:
    check_budget(deadline)
    lines = complete_lines(os.pread(fd, MAX_HEAD_BYTES, 0), False, True, deadline)
    if not lines:
        return False
    try:
        record = json.loads(lines[0])
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return False
    if not isinstance(record, dict) or record.get("type") != "session_meta":
        return False
    payload = record.get("payload")
    return isinstance(payload, dict) and payload.get("id") == thread_id


def normalize_timestamp(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    utc = parsed.astimezone(timezone.utc)
    if utc > datetime.now(timezone.utc) + timedelta(minutes=5):
        return None
    return utc.isoformat(timespec="seconds").replace("+00:00", "Z")


def read_latest_setting(
    fd: int,
    size: int,
    deadline: float,
) -> tuple[dict[str, Any] | None, str | None]:
    check_budget(deadline)
    offset = max(0, size - MAX_TAIL_BYTES)
    tail = os.pread(fd, min(size, MAX_TAIL_BYTES), offset)
    lines = complete_lines(tail, offset > 0, True, deadline)
    if len(lines) > MAX_TAIL_LINES:
        lines = lines[-MAX_TAIL_LINES:]
    latest: dict[str, Any] | None = None
    for raw in lines:
        check_budget(deadline)
        try:
            record = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
            if latest is not None:
                return None, "corrupt_record_after_setting"
            continue
        if not isinstance(record, dict):
            if latest is not None:
                return None, "corrupt_record_after_setting"
            continue
        if record.get("type") == "turn_context":
            latest = record
    if latest is None:
        return None, "turn_context_not_found"
    payload = latest.get("payload")
    if not isinstance(payload, dict):
        return None, "invalid_latest_setting"
    model = payload.get("model")
    effort = payload.get("effort")
    observed_at = normalize_timestamp(latest.get("timestamp"))
    if (
        not isinstance(model, str)
        or not MODEL_PATTERN.fullmatch(model)
        or not isinstance(effort, str)
        or effort not in EFFORTS
        or observed_at is None
    ):
        return None, "invalid_latest_setting"
    current = {
        "evidence_status": "verified",
        "model": model,
        "effort": effort,
        "observed_at": observed_at,
    }
    content = {"model": model, "effort": effort, "observed_at": observed_at}
    content_sha256 = canonical_sha256(content)
    provenance = {
        "schema_version": "1.0",
        "receipt_id": f"session-current-{content_sha256[:24]}",
        "evidence_kind": "current_setting",
        "source": "local_session_turn_context",
        "observed_at": observed_at,
        "ttl_seconds": PROVENANCE_TTL_SECONDS,
        "content_sha256": content_sha256,
    }
    return {
        "status": "verified",
        "current": current,
        "current_provenance": provenance,
    }, None


def main() -> int:
    deadline = time.monotonic() + TIME_BUDGET_SECONDS
    thread_id = os.environ.get("CODEX_THREAD_ID", "")
    if not thread_id:
        return unknown("missing_thread_id")
    if not THREAD_ID_PATTERN.fullmatch(thread_id):
        return unknown("invalid_thread_id")
    codex_home = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()
    candidates, error = iter_candidates(codex_home, thread_id, deadline)
    if error:
        return unknown(error)
    verified: list[tuple[int, os.stat_result]] = []
    try:
        for candidate in candidates:
            check_budget(deadline)
            fd, info, file_error = secure_open(candidate)
            if file_error or fd is None or info is None:
                return unknown(file_error or "session_unreadable")
            if exact_session_meta(fd, thread_id, deadline):
                verified.append((fd, info))
            else:
                os.close(fd)
        if len(verified) != 1:
            for fd, _ in verified:
                os.close(fd)
            return unknown("ambiguous_session" if verified else "session_meta_mismatch")
        fd, info = verified[0]
        try:
            result, error = read_latest_setting(fd, info.st_size, deadline)
            final = os.fstat(fd)
            if (
                (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
                != (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)
                or not stat.S_ISREG(final.st_mode)
                or final.st_uid != os.getuid()
                or final.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                or final.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                or final.st_nlink != 1
            ):
                return unknown("session_changed_during_read")
        finally:
            os.close(fd)
    except TimeoutError:
        return unknown("time_budget_exceeded")
    except (OSError, ValueError, json.JSONDecodeError):
        return unknown("session_unreadable")
    if error or result is None:
        return unknown(error or "invalid_latest_setting")
    return emit(result)


if __name__ == "__main__":
    raise SystemExit(main())
