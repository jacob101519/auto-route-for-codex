#!/usr/bin/env python3
"""Persist and advance a capability-gated Codex fork transfer."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import secrets
import stat
import tempfile
from pathlib import Path
from typing import Any, Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - unsupported Desktop host
    fcntl = None

from route_task import KNOWN_EFFORTS, MODEL_PATTERN, canonical_sha256, parse_time, recommend


__all__: tuple[str, ...] = ()


ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
LEASE_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CONFIRMED_STATES = (
    "fork_created",
    "prompt_delivery_confirmed",
    "destination_readback_confirmed",
    "navigation_confirmed",
    "source_archive_confirmed",
)
PREVIOUS = {
    "fork_created": "planned",
    "prompt_delivery_confirmed": "fork_created",
    "destination_readback_confirmed": "prompt_delivery_confirmed",
    "navigation_confirmed": "destination_readback_confirmed",
    "source_archive_confirmed": "navigation_confirmed",
}
UNCERTAIN_EVENTS = {
    "timeout",
    "ambiguous_result",
    "delivery_unknown",
    "incomplete_result",
    "thread_id_mismatch",
    "prompt_digest_mismatch",
}
MAX_STATE_BYTES = 16 * 1024


def _authorization_reference_time(router_input: dict[str, Any]):
    provenance_fields = ("current_provenance", "catalog_provenance", "host_provenance")
    try:
        observed = [parse_time(router_input[field]["observed_at"]) for field in provenance_fields]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid_authorization_reference") from exc
    return max(observed)


def _authorized_route(router_input: dict[str, Any], *, require_fresh: bool) -> dict[str, Any]:
    if not isinstance(router_input, dict):
        raise ValueError("invalid_router_input")
    route = recommend(
        router_input,
        now=None if require_fresh else _authorization_reference_time(router_input),
    )
    decision = route["decision"]
    eligible = (
        decision["action"] == "reroute"
        and decision["benefit"] in {"quality", "parallelism"}
        and decision["transfer"] == "fork"
        and decision["source_disposition"] == "archive_after_continuation_ready"
        and decision["evidence_status"] == "verified"
        and route["evidence"]["aggregate_status"] == "verified"
        and route["evidence"]["continuation_capable"] is True
        and route["tool_overrides"] is not None
    )
    if not eligible:
        raise ValueError("route_not_authorized")
    return route


def _authorization_binding(
    source_binding_sha256: str,
    transfer_id: str,
    prompt_sha256: str,
    router_input_sha256: str,
    route_authorization: str,
    recommended_model: str,
    recommended_thinking: str,
) -> str:
    return canonical_sha256({
        "source_binding_sha256": source_binding_sha256,
        "transfer_id": transfer_id,
        "prompt_sha256": prompt_sha256,
        "router_input_sha256": router_input_sha256,
        "route_authorization": route_authorization,
        "recommended_model": recommended_model,
        "recommended_thinking": recommended_thinking,
    })


def _confirmed_state_chain(receipt: dict[str, Any]) -> str:
    chain = canonical_sha256({
        "authorization_binding": receipt["authorization_binding"],
        "source_binding_sha256": receipt["source_binding_sha256"],
        "state": "planned",
    })
    for event in receipt["confirmed_events"]:
        chain = canonical_sha256({
            "previous": chain,
            "event": event,
            "destination_thread_id": receipt["destination_thread_id"],
            "prompt_sha256": receipt["prompt_sha256"]
            if event in {"prompt_delivery_confirmed", "destination_readback_confirmed"}
            else None,
            "recommended_model": receipt["recommended_model"]
            if event == "prompt_delivery_confirmed"
            else None,
            "recommended_thinking": receipt["recommended_thinking"]
            if event == "prompt_delivery_confirmed"
            else None,
        })
    return chain


def _expected_state_chain(receipt: dict[str, Any]) -> str:
    chain = _confirmed_state_chain(receipt)
    pending = receipt.get("pending_reservation")
    if pending is not None:
        chain = canonical_sha256({"previous": chain, "pending_reservation": pending})
    if receipt["state"] == "uncertain":
        chain = canonical_sha256({
            "previous": chain,
            "event": "uncertain",
            "reason": receipt["uncertainty_reason"],
        })
    return chain


def _mark_uncertain(receipt: dict[str, Any], reason: str) -> dict[str, Any]:
    if not isinstance(reason, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", reason):
        raise ValueError("invalid_uncertainty_reason")
    result = dict(receipt)
    result["confirmed_events"] = list(receipt["confirmed_events"])
    pending = receipt.get("pending_reservation")
    result["pending_reservation"] = dict(pending) if isinstance(pending, dict) else None
    result["state"] = "uncertain"
    result["archive_authorized"] = False
    result["uncertainty_reason"] = reason
    result["state_chain_sha256"] = _expected_state_chain(result)
    return result


def _directory_is_safe(path: Path, *, owner_only: bool) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    forbidden = (stat.S_IRWXG | stat.S_IRWXO) if owner_only else (stat.S_IWGRP | stat.S_IWOTH)
    return (
        stat.S_ISDIR(info.st_mode)
        and not stat.S_ISLNK(info.st_mode)
        and info.st_uid == os.getuid()
        and not info.st_mode & forbidden
    )


def _fsync_directory(path: Path) -> None:
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("nofollow_unavailable")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
        try:
            info = os.fstat(fd)
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError("unsafe_state_directory")
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise ValueError("state_directory_sync_failed") from exc


def _ensure_child_directory(parent: Path, name: str, *, owner_only: bool = True) -> Path:
    if not _directory_is_safe(parent, owner_only=False):
        raise ValueError("unsafe_state_parent")
    child = parent / name
    created = False
    try:
        os.mkdir(child, mode=0o700)
        created = True
    except FileExistsError:
        pass
    except OSError as exc:
        raise ValueError("state_directory_create_failed") from exc
    if not _directory_is_safe(child, owner_only=owner_only):
        raise ValueError("unsafe_state_directory")
    if created:
        _fsync_directory(parent)
    return child


def _reservation_root() -> Path:
    configured = os.environ.get("AUTO_ROUTE_STATE_HOME")
    if configured:
        root = Path(configured).expanduser()
        if not root.is_absolute() or not _directory_is_safe(root, owner_only=True):
            raise ValueError("unsafe_state_root")
        return root
    codex_home = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()
    if not codex_home.is_absolute() or not _directory_is_safe(codex_home, owner_only=False):
        raise ValueError("unsafe_codex_home")
    state_root = _ensure_child_directory(codex_home, "state", owner_only=False)
    return _ensure_child_directory(state_root, "auto-route-for-codex", owner_only=True)


def _source_binding_sha256() -> str:
    thread_id = os.environ.get("CODEX_THREAD_ID")
    if not isinstance(thread_id, str) or not ID_PATTERN.fullmatch(thread_id):
        raise ValueError("source_thread_context_required")
    return canonical_sha256({
        "namespace": "auto-route-for-codex/source-task/v1",
        "source_thread_id": thread_id,
    })


def _reservation_directory(source_binding_sha256: str | None = None) -> Path:
    source_binding_sha256 = source_binding_sha256 or _source_binding_sha256()
    if not isinstance(source_binding_sha256, str) or not SHA256_PATTERN.fullmatch(source_binding_sha256):
        raise ValueError("invalid_source_binding_sha256")
    return _ensure_child_directory(
        _reservation_root(),
        canonical_sha256({"source_binding_sha256": source_binding_sha256}),
        owner_only=True,
    )


@contextlib.contextmanager
def _locked_transfer(source_binding_sha256: str) -> Iterator[Path]:
    if fcntl is None or not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("atomic_lock_unavailable")
    directory = _reservation_directory(source_binding_sha256)
    lock_path = directory / "transfer.lock"
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
    try:
        existed = os.path.lexists(lock_path)
        fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise ValueError("transfer_lock_unavailable") from exc
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & (stat.S_IRWXG | stat.S_IRWXO)
            or info.st_nlink != 1
        ):
            raise ValueError("unsafe_transfer_lock")
        if not existed:
            _fsync_directory(directory)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield directory
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _canonical_receipt_path(directory: Path) -> Path:
    return directory / "receipt.json"


def _read_state_file(path: Path) -> dict[str, Any]:
    try:
        if not hasattr(os, "O_NOFOLLOW"):
            raise ValueError("nofollow_unavailable")
        before = path.lstat()
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_ISLNK(before.st_mode)
            or before.st_uid != os.getuid()
            or before.st_mode & (stat.S_IRWXG | stat.S_IRWXO)
            or before.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            or before.st_nlink != 1
            or before.st_size > MAX_STATE_BYTES
        ):
            raise ValueError("unsafe_state_file")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW)
        try:
            after = os.fstat(fd)
            if (
                (before.st_dev, before.st_ino, before.st_size)
                != (after.st_dev, after.st_ino, after.st_size)
                or not stat.S_ISREG(after.st_mode)
                or after.st_uid != os.getuid()
                or after.st_mode & (stat.S_IRWXG | stat.S_IRWXO)
                or after.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                or after.st_nlink != 1
            ):
                raise ValueError("state_file_changed_during_read")
            data = os.read(fd, MAX_STATE_BYTES + 1)
        finally:
            os.close(fd)
        if len(data) > MAX_STATE_BYTES:
            raise ValueError("unsafe_state_file")
        value = json.loads(data)
    except FileNotFoundError as exc:
        raise ValueError("state_file_missing") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("state_file_unreadable") from exc
    if not isinstance(value, dict):
        raise ValueError("state_file_unreadable")
    return value


def _atomic_write_receipt(directory: Path, receipt: dict[str, Any]) -> None:
    data = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("ascii")
    if len(data) > MAX_STATE_BYTES:
        raise ValueError("receipt_too_large")
    fd, temporary_name = tempfile.mkstemp(prefix=".receipt-", dir=directory)
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(fd, 0o600)
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("receipt_write_failed")
            view = view[written:]
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.replace(temporary_path, _canonical_receipt_path(directory))
        _fsync_directory(directory)
    except OSError as exc:
        raise ValueError("receipt_write_failed") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def _load_canonical_receipt(directory: Path) -> dict[str, Any]:
    return _read_state_file(_canonical_receipt_path(directory))


def _reservation_payload(
    receipt: dict[str, Any],
    event: str,
    destination_thread_id: str | None,
    prompt_sha256: str | None,
    observed_model: str | None,
    observed_thinking: str | None,
    *,
    lease_sha256: str,
    prior_state_chain_sha256: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "source_binding_sha256": receipt["source_binding_sha256"],
        "transfer_id": receipt["transfer_id"],
        "authorization_binding": receipt["authorization_binding"],
        "prior_state_chain_sha256": prior_state_chain_sha256 or receipt["state_chain_sha256"],
        "event": event,
        "destination_thread_id": destination_thread_id,
        "prompt_sha256": prompt_sha256,
        "recommended_model": observed_model if event == "prompt_delivery_confirmed" else None,
        "recommended_thinking": observed_thinking if event == "prompt_delivery_confirmed" else None,
        "lease_sha256": lease_sha256,
    }


def _validate_reservation_request(
    receipt: dict[str, Any],
    event: str,
    destination_thread_id: str | None,
    prompt_sha256: str | None,
    observed_model: str | None,
    observed_thinking: str | None,
) -> None:
    if event not in CONFIRMED_STATES:
        raise ValueError("invalid_reservation_event")
    if receipt["state"] == "uncertain":
        raise ValueError("transfer_uncertain")
    if receipt["pending_reservation"] is not None:
        raise ValueError("reservation_pending")
    if event in receipt["confirmed_events"]:
        raise ValueError("event_already_confirmed")
    if receipt["state"] != PREVIOUS[event]:
        raise ValueError("invalid_transition")
    if event == "fork_created":
        if destination_thread_id is not None:
            raise ValueError("destination_must_be_unknown_before_fork")
    elif (
        not destination_thread_id
        or destination_thread_id != receipt["destination_thread_id"]
    ):
        raise ValueError("destination_thread_id_mismatch")
    digest_required = event in {"prompt_delivery_confirmed", "destination_readback_confirmed"}
    if digest_required and prompt_sha256 != receipt["prompt_sha256"]:
        raise ValueError("prompt_digest_mismatch")
    if not digest_required and prompt_sha256 is not None:
        raise ValueError("unexpected_prompt_digest")
    if event == "prompt_delivery_confirmed":
        if (
            observed_model != receipt["recommended_model"]
            or observed_thinking != receipt["recommended_thinking"]
        ):
            raise ValueError("destination_setting_mismatch")
    elif observed_model is not None or observed_thinking is not None:
        raise ValueError("unexpected_destination_setting")
    if event == "source_archive_confirmed" and not receipt["archive_authorized"]:
        raise ValueError("archive_not_authorized")


def _validate_confirmed_event_replay(
    receipt: dict[str, Any],
    event: str,
    destination_thread_id: str | None,
    prompt_sha256: str | None,
    observed_model: str | None,
    observed_thinking: str | None,
) -> None:
    if destination_thread_id != receipt["destination_thread_id"]:
        raise ValueError("destination_thread_id_mismatch")
    digest_required = event in {"prompt_delivery_confirmed", "destination_readback_confirmed"}
    if digest_required and prompt_sha256 != receipt["prompt_sha256"]:
        raise ValueError("prompt_digest_mismatch")
    if not digest_required and prompt_sha256 is not None:
        raise ValueError("unexpected_prompt_digest")
    if event == "prompt_delivery_confirmed":
        if (
            observed_model != receipt["recommended_model"]
            or observed_thinking != receipt["recommended_thinking"]
        ):
            raise ValueError("destination_setting_mismatch")
    elif observed_model is not None or observed_thinking is not None:
        raise ValueError("unexpected_destination_setting")


def _write_reservation(path: Path, payload: dict[str, Any]) -> bool:
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("nofollow_unavailable")
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    if len(data) > MAX_STATE_BYTES:
        raise ValueError("reservation_too_large")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        return False
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("reservation_write_failed")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_directory(path.parent)
    return True


def _new_receipt(
    transfer_id: str,
    prompt_sha256: str,
    router_input: dict[str, Any],
    *,
    source_binding_sha256: str | None = None,
) -> dict[str, Any]:
    if not isinstance(transfer_id, str) or not ID_PATTERN.fullmatch(transfer_id):
        raise ValueError("invalid_transfer_id")
    if not isinstance(prompt_sha256, str) or not SHA256_PATTERN.fullmatch(prompt_sha256):
        raise ValueError("invalid_prompt_sha256")
    source_binding_sha256 = source_binding_sha256 or _source_binding_sha256()
    if not isinstance(source_binding_sha256, str) or not SHA256_PATTERN.fullmatch(source_binding_sha256):
        raise ValueError("invalid_source_binding_sha256")
    route = _authorized_route(router_input, require_fresh=True)
    route_authorization = route["route_authorization"]
    if not isinstance(route_authorization, str) or not SHA256_PATTERN.fullmatch(route_authorization):
        raise ValueError("invalid_route_authorization")
    recommended_model = route["tool_overrides"]["model"]
    recommended_thinking = route["tool_overrides"]["thinking"]
    router_input_sha256 = canonical_sha256(router_input)
    binding = _authorization_binding(
        source_binding_sha256,
        transfer_id,
        prompt_sha256,
        router_input_sha256,
        route_authorization,
        recommended_model,
        recommended_thinking,
    )
    receipt = {
        "schema_version": "1.0",
        "source_binding_sha256": source_binding_sha256,
        "transfer_id": transfer_id,
        "state": "planned",
        "source_disposition": "archive_after_continuation_ready",
        "prompt_sha256": prompt_sha256,
        "router_input_sha256": router_input_sha256,
        "route_authorization": route_authorization,
        "authorization_binding": binding,
        "recommended_model": recommended_model,
        "recommended_thinking": recommended_thinking,
        "destination_thread_id": None,
        "archive_authorized": False,
        "confirmed_events": [],
        "pending_reservation": None,
    }
    receipt["state_chain_sha256"] = _expected_state_chain(receipt)
    return receipt


def _validate_receipt(
    receipt: dict[str, Any],
    router_input: dict[str, Any],
    *,
    source_binding_sha256: str | None = None,
) -> None:
    required = {
        "schema_version",
        "source_binding_sha256",
        "transfer_id",
        "state",
        "source_disposition",
        "destination_thread_id",
        "archive_authorized",
        "confirmed_events",
        "pending_reservation",
        "prompt_sha256",
        "router_input_sha256",
        "route_authorization",
        "authorization_binding",
        "recommended_model",
        "recommended_thinking",
        "state_chain_sha256",
    }
    if not isinstance(receipt, dict) or not required.issubset(receipt):
        raise ValueError("invalid_receipt")
    if set(receipt) - (required | {"uncertainty_reason"}):
        raise ValueError("invalid_receipt")
    if receipt["schema_version"] != "1.0":
        raise ValueError("invalid_schema_version")
    source_binding_sha256 = source_binding_sha256 or _source_binding_sha256()
    if not isinstance(source_binding_sha256, str) or not SHA256_PATTERN.fullmatch(source_binding_sha256):
        raise ValueError("invalid_source_binding_sha256")
    if receipt["source_binding_sha256"] != source_binding_sha256:
        raise ValueError("source_binding_mismatch")
    if not isinstance(receipt["transfer_id"], str) or not ID_PATTERN.fullmatch(receipt["transfer_id"]):
        raise ValueError("invalid_transfer_id")
    if not isinstance(receipt["state"], str) or receipt["state"] not in {"planned", "uncertain", *CONFIRMED_STATES}:
        raise ValueError("invalid_state")
    if receipt["source_disposition"] != "archive_after_continuation_ready":
        raise ValueError("invalid_source_disposition")
    if type(receipt["archive_authorized"]) is not bool:
        raise ValueError("invalid_archive_authorization")
    if not isinstance(receipt["prompt_sha256"], str) or not SHA256_PATTERN.fullmatch(receipt["prompt_sha256"]):
        raise ValueError("invalid_prompt_sha256")
    for field in (
        "router_input_sha256",
        "route_authorization",
        "authorization_binding",
        "state_chain_sha256",
    ):
        if not isinstance(receipt[field], str) or not SHA256_PATTERN.fullmatch(receipt[field]):
            raise ValueError(f"invalid_{field}")
    if (
        not isinstance(receipt["recommended_model"], str)
        or receipt["recommended_model"] == "unknown"
        or not MODEL_PATTERN.fullmatch(receipt["recommended_model"])
    ):
        raise ValueError("invalid_recommended_model")
    if receipt["recommended_thinking"] not in KNOWN_EFFORTS:
        raise ValueError("invalid_recommended_thinking")
    destination = receipt["destination_thread_id"]
    if destination is not None and (
        not isinstance(destination, str) or not ID_PATTERN.fullmatch(destination)
    ):
        raise ValueError("invalid_destination_thread_id")
    events = receipt["confirmed_events"]
    if (
        not isinstance(events, list)
        or any(not isinstance(event, str) or event not in CONFIRMED_STATES for event in events)
        or len(events) != len(set(events))
        or events != list(CONFIRMED_STATES[: len(events)])
    ):
        raise ValueError("invalid_confirmed_events")
    if bool(events) != (destination is not None):
        raise ValueError("invalid_destination_binding")
    if receipt["state"] not in {"planned", "uncertain"} and receipt["state"] != (events[-1] if events else None):
        raise ValueError("invalid_state")
    if receipt["state"] == "planned" and events:
        raise ValueError("invalid_planned_receipt")
    expected_archive = (
        receipt["state"] == "navigation_confirmed"
        and receipt["source_disposition"] == "archive_after_continuation_ready"
    )
    if receipt["archive_authorized"] is not expected_archive:
        raise ValueError("invalid_archive_authorization")
    if receipt["state"] == "uncertain" and not isinstance(receipt.get("uncertainty_reason"), str):
        raise ValueError("invalid_uncertainty_reason")
    if receipt["state"] != "uncertain" and "uncertainty_reason" in receipt:
        raise ValueError("invalid_uncertainty_reason")

    pending = receipt["pending_reservation"]
    if pending is not None:
        pending_keys = {
            "event",
            "reservation_sha256",
            "lease_sha256",
            "prior_state_chain_sha256",
        }
        if not isinstance(pending, dict) or set(pending) != pending_keys:
            raise ValueError("invalid_pending_reservation")
        if (
            pending["event"] not in CONFIRMED_STATES
            or any(
                not isinstance(pending[field], str) or not SHA256_PATTERN.fullmatch(pending[field])
                for field in ("reservation_sha256", "lease_sha256", "prior_state_chain_sha256")
            )
        ):
            raise ValueError("invalid_pending_reservation")
        next_event = CONFIRMED_STATES[len(events)] if len(events) < len(CONFIRMED_STATES) else None
        if pending["event"] != next_event:
            raise ValueError("invalid_pending_event")
        if pending["prior_state_chain_sha256"] != _confirmed_state_chain(receipt):
            raise ValueError("invalid_pending_prior_state")
    if receipt["state"] == "source_archive_confirmed" and pending is not None:
        raise ValueError("invalid_pending_reservation")

    route = _authorized_route(router_input, require_fresh=False)
    router_input_sha256 = canonical_sha256(router_input)
    if receipt["router_input_sha256"] != router_input_sha256:
        raise ValueError("router_input_binding_mismatch")
    if receipt["route_authorization"] != route["route_authorization"]:
        raise ValueError("route_authorization_mismatch")
    overrides = route["tool_overrides"]
    if (
        receipt["recommended_model"] != overrides["model"]
        or receipt["recommended_thinking"] != overrides["thinking"]
    ):
        raise ValueError("recommended_setting_mismatch")
    expected_binding = _authorization_binding(
        source_binding_sha256,
        receipt["transfer_id"],
        receipt["prompt_sha256"],
        router_input_sha256,
        receipt["route_authorization"],
        receipt["recommended_model"],
        receipt["recommended_thinking"],
    )
    if receipt["authorization_binding"] != expected_binding:
        raise ValueError("authorization_binding_mismatch")
    if receipt["state_chain_sha256"] != _expected_state_chain(receipt):
        raise ValueError("state_chain_mismatch")


def _create_stateful_receipt(
    transfer_id: str,
    prompt_sha256: str,
    router_input: dict[str, Any],
) -> dict[str, Any]:
    source_binding_sha256 = _source_binding_sha256()
    with _locked_transfer(source_binding_sha256) as directory:
        path = _canonical_receipt_path(directory)
        if os.path.lexists(path):
            existing = _load_canonical_receipt(directory)
            _validate_receipt(
                existing,
                router_input,
                source_binding_sha256=source_binding_sha256,
            )
            if existing["transfer_id"] != transfer_id:
                raise ValueError("source_task_already_bound")
            if (
                existing["prompt_sha256"] != prompt_sha256
                or existing["router_input_sha256"] != canonical_sha256(router_input)
            ):
                raise ValueError("transfer_id_already_bound")
            return existing
        proposed = _new_receipt(
            transfer_id,
            prompt_sha256,
            router_input,
            source_binding_sha256=source_binding_sha256,
        )
        _atomic_write_receipt(directory, proposed)
        return proposed


def _reconcile_result(event: str, reason: str) -> dict[str, Any]:
    return {
        "status": "reconcile_required",
        "event": event,
        "side_effect_authorized": False,
        "reason": reason,
    }


def _reserve_stateful_event(
    transfer_id: str,
    event: str,
    destination_thread_id: str | None = None,
    prompt_sha256: str | None = None,
    *,
    router_input: dict[str, Any],
    observed_model: str | None = None,
    observed_thinking: str | None = None,
) -> dict[str, Any]:
    source_binding_sha256 = _source_binding_sha256()
    with _locked_transfer(source_binding_sha256) as directory:
        receipt = _load_canonical_receipt(directory)
        _validate_receipt(
            receipt,
            router_input,
            source_binding_sha256=source_binding_sha256,
        )
        if receipt["transfer_id"] != transfer_id:
            raise ValueError("transfer_id_mismatch")
        if receipt["state"] == "uncertain":
            return _reconcile_result(event, "transfer_uncertain")
        pending = receipt["pending_reservation"]
        if pending is not None:
            return _reconcile_result(event, "canonical_reservation_pending")
        _authorized_route(router_input, require_fresh=True)
        _validate_reservation_request(
            receipt,
            event,
            destination_thread_id,
            prompt_sha256,
            observed_model,
            observed_thinking,
        )
        marker_path = directory / f"{event}.json"
        if os.path.lexists(marker_path):
            return _reconcile_result(event, "reservation_marker_exists")
        reservation_lease = secrets.token_hex(32)
        lease_sha256 = canonical_sha256({"reservation_lease": reservation_lease})
        payload = _reservation_payload(
            receipt,
            event,
            destination_thread_id,
            prompt_sha256,
            observed_model,
            observed_thinking,
            lease_sha256=lease_sha256,
        )
        reservation_sha256 = canonical_sha256(payload)
        if not _write_reservation(marker_path, payload):
            return _reconcile_result(event, "reservation_marker_exists")
        updated = dict(receipt)
        updated["confirmed_events"] = list(receipt["confirmed_events"])
        updated["pending_reservation"] = {
            "event": event,
            "reservation_sha256": reservation_sha256,
            "lease_sha256": lease_sha256,
            "prior_state_chain_sha256": receipt["state_chain_sha256"],
        }
        updated["state_chain_sha256"] = _expected_state_chain(updated)
        _atomic_write_receipt(directory, updated)
        return {
            "status": "reserved",
            "event": event,
            "side_effect_authorized": True,
            "reservation_sha256": reservation_sha256,
            "reservation_lease": reservation_lease,
        }


def _confirmation_mismatch_reason(
    receipt: dict[str, Any],
    event: str,
    destination_thread_id: str | None,
    prompt_sha256: str | None,
    observed_model: str | None,
    observed_thinking: str | None,
) -> str | None:
    if event == "fork_created":
        if not destination_thread_id:
            return "destination_thread_id_missing"
        if not ID_PATTERN.fullmatch(destination_thread_id):
            return "thread_id_mismatch"
    elif destination_thread_id != receipt["destination_thread_id"]:
        return "destination_thread_id_missing" if not destination_thread_id else "thread_id_mismatch"
    digest_required = event in {"prompt_delivery_confirmed", "destination_readback_confirmed"}
    if digest_required and prompt_sha256 != receipt["prompt_sha256"]:
        return "prompt_digest_mismatch"
    if not digest_required and prompt_sha256 is not None:
        return "prompt_digest_mismatch"
    if event == "prompt_delivery_confirmed":
        if (
            observed_model != receipt["recommended_model"]
            or observed_thinking != receipt["recommended_thinking"]
        ):
            return "destination_setting_mismatch"
    elif observed_model is not None or observed_thinking is not None:
        return "destination_setting_mismatch"
    return None


def _expected_marker_from_pending(receipt: dict[str, Any]) -> dict[str, Any]:
    pending = receipt["pending_reservation"]
    if not isinstance(pending, dict):
        raise ValueError("reservation_required")
    event = pending["event"]
    destination = None if event == "fork_created" else receipt["destination_thread_id"]
    prompt = receipt["prompt_sha256"] if event in {
        "prompt_delivery_confirmed",
        "destination_readback_confirmed",
    } else None
    model = receipt["recommended_model"] if event == "prompt_delivery_confirmed" else None
    thinking = receipt["recommended_thinking"] if event == "prompt_delivery_confirmed" else None
    return _reservation_payload(
        receipt,
        event,
        destination,
        prompt,
        model,
        thinking,
        lease_sha256=pending["lease_sha256"],
        prior_state_chain_sha256=pending["prior_state_chain_sha256"],
    )


def _confirm_stateful_event(
    transfer_id: str,
    event: str,
    destination_thread_id: str | None = None,
    prompt_sha256: str | None = None,
    *,
    router_input: dict[str, Any],
    reservation_lease: str | None = None,
    observed_model: str | None = None,
    observed_thinking: str | None = None,
) -> dict[str, Any]:
    source_binding_sha256 = _source_binding_sha256()
    with _locked_transfer(source_binding_sha256) as directory:
        receipt = _load_canonical_receipt(directory)
        _validate_receipt(
            receipt,
            router_input,
            source_binding_sha256=source_binding_sha256,
        )
        if receipt["transfer_id"] != transfer_id:
            raise ValueError("transfer_id_mismatch")
        if event in UNCERTAIN_EVENTS:
            if receipt["state"] == "uncertain":
                return receipt
            result = _mark_uncertain(receipt, event)
            _atomic_write_receipt(directory, result)
            return result
        if event not in CONFIRMED_STATES:
            raise ValueError("invalid_event")
        if event in receipt["confirmed_events"]:
            _validate_confirmed_event_replay(
                receipt,
                event,
                destination_thread_id,
                prompt_sha256,
                observed_model,
                observed_thinking,
            )
            return receipt
        if receipt["state"] == "uncertain":
            raise ValueError("transfer_uncertain")
        pending = receipt["pending_reservation"]
        if not isinstance(pending, dict) or pending["event"] != event:
            raise ValueError("reservation_required")
        if not isinstance(reservation_lease, str) or not LEASE_PATTERN.fullmatch(reservation_lease):
            raise ValueError("reservation_lease_required")
        if canonical_sha256({"reservation_lease": reservation_lease}) != pending["lease_sha256"]:
            raise ValueError("reservation_lease_mismatch")
        expected_marker = _expected_marker_from_pending(receipt)
        if canonical_sha256(expected_marker) != pending["reservation_sha256"]:
            raise ValueError("reservation_binding_mismatch")
        marker_path = directory / f"{event}.json"
        if _read_state_file(marker_path) != expected_marker:
            raise ValueError("reservation_conflict")
        mismatch = _confirmation_mismatch_reason(
            receipt,
            event,
            destination_thread_id,
            prompt_sha256,
            observed_model,
            observed_thinking,
        )
        if mismatch:
            result = _mark_uncertain(receipt, mismatch)
            _atomic_write_receipt(directory, result)
            return result

        result = dict(receipt)
        result["confirmed_events"] = list(receipt["confirmed_events"])
        result["pending_reservation"] = None
        result["state"] = event
        result["confirmed_events"].append(event)
        if event == "fork_created":
            result["destination_thread_id"] = destination_thread_id
        result["archive_authorized"] = (
            event == "navigation_confirmed"
            and receipt["source_disposition"] == "archive_after_continuation_ready"
        )
        if event == "source_archive_confirmed":
            result["archive_authorized"] = False
        result.pop("uncertainty_reason", None)
        result["state_chain_sha256"] = _expected_state_chain(result)
        _atomic_write_receipt(directory, result)
        return result


def _compact_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    pending = receipt.get("pending_reservation")
    return {
        "status": "uncertain" if receipt["state"] == "uncertain" else "recorded",
        "transfer_id": receipt["transfer_id"],
        "state": receipt["state"],
        "destination_thread_id": receipt["destination_thread_id"],
        "archive_authorized": receipt["archive_authorized"],
        "pending_event": pending["event"] if isinstance(pending, dict) else None,
        "reconcile_required": receipt["state"] == "uncertain" or pending is not None,
        "state_chain_sha256": receipt["state_chain_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--new", action="store_true")
    parser.add_argument("--router-input", type=Path)
    parser.add_argument("--transfer-id")
    parser.add_argument("--event", choices=CONFIRMED_STATES + tuple(sorted(UNCERTAIN_EVENTS)))
    parser.add_argument("--reserve-event", choices=CONFIRMED_STATES)
    parser.add_argument("--destination-thread-id")
    parser.add_argument("--prompt-sha256")
    parser.add_argument("--observed-model")
    parser.add_argument("--observed-thinking")
    parser.add_argument("--reservation-lease")
    args = parser.parse_args()
    try:
        if args.new:
            if not args.transfer_id or not args.prompt_sha256 or not args.router_input:
                parser.error("--transfer-id, --prompt-sha256, and --router-input are required with --new")
            result = _compact_receipt(_create_stateful_receipt(
                args.transfer_id,
                args.prompt_sha256,
                json.loads(args.router_input.read_text(encoding="utf-8")),
            ))
        else:
            if not args.transfer_id or not args.router_input or bool(args.event) == bool(args.reserve_event):
                parser.error("--transfer-id, --router-input, and exactly one of --event or --reserve-event are required")
            router_input = json.loads(args.router_input.read_text(encoding="utf-8"))
            selected_event = args.reserve_event or args.event
            if args.reserve_event:
                result = _reserve_stateful_event(
                    args.transfer_id,
                    selected_event,
                    args.destination_thread_id,
                    args.prompt_sha256,
                    router_input=router_input,
                    observed_model=args.observed_model,
                    observed_thinking=args.observed_thinking,
                )
            else:
                result = _compact_receipt(_confirm_stateful_event(
                    args.transfer_id,
                    selected_event,
                    args.destination_thread_id,
                    args.prompt_sha256,
                    router_input=router_input,
                    reservation_lease=args.reservation_lease,
                    observed_model=args.observed_model,
                    observed_thinking=args.observed_thinking,
                ))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
