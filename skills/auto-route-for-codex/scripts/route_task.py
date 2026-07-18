#!/usr/bin/env python3
"""Produce a deterministic, recommendation-only public routing result."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra")
CURRENT_EFFORTS = ("unknown",) + EFFORTS
EFFORT_RANK = {value: index for index, value in enumerate(EFFORTS)}
DEEP_KINDS = {"architecture", "migration", "deep_research", "final_decision"}
TASK_KINDS = {"simple_answer", "local_edit", "implementation", *DEEP_KINDS, "batch"}
PROFILE_FIELDS = {
    "task_kind", "scope", "risk", "duration", "priority", "ambiguity",
    "verification_strength", "context_portability", "architecture_signals",
    "repeated_failures", "parallel_workstreams", "coupling",
    "independently_verifiable", "write_conflict_risk", "delegation_authorized",
    "parallelism_observed", "single_hard_problem", "max_insufficient_evidence",
}
PROFILE_REQUIRED = {"task_kind", "scope", "risk", "duration", "priority"}
MODEL_PATTERN = re.compile(r"^(?:unknown|[A-Za-z0-9][A-Za-z0-9._+-]{0,127})$")
RECEIPT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


MAX_TTL = {"catalog": 604800, "host_capability": 600}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def parse_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("invalid_timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("invalid_timestamp")
    return parsed


def validate_provenance(value: Any, kind: str, source: str, payload: dict[str, Any]) -> bool:
    keys = {"schema_version", "receipt_id", "evidence_kind", "source", "observed_at", "ttl_seconds", "content_sha256"}
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("invalid_provenance")
    if value["schema_version"] != "1.0" or value["evidence_kind"] != kind or value["source"] != source:
        raise ValueError("invalid_provenance")
    if not isinstance(value["receipt_id"], str) or not RECEIPT_ID_PATTERN.fullmatch(value["receipt_id"]):
        raise ValueError("invalid_provenance")
    if not isinstance(value["observed_at"], str) or not value["observed_at"]:
        raise ValueError("invalid_provenance")
    if type(value["ttl_seconds"]) is not int or not 1 <= value["ttl_seconds"] <= MAX_TTL[kind]:
        raise ValueError("invalid_provenance")
    if not isinstance(value["content_sha256"], str) or len(value["content_sha256"]) != 64 or any(char not in "0123456789abcdef" for char in value["content_sha256"]):
        raise ValueError("invalid_provenance")
    try:
        observed = parse_time(value["observed_at"])
    except ValueError:
        return False
    now = datetime.now(timezone.utc)
    return (
        observed <= now + timedelta(minutes=5)
        and now <= observed + timedelta(seconds=value["ttl_seconds"])
        and value["content_sha256"] == canonical_sha256(payload)
    )


def validate_profile(profile: Any) -> None:
    if not isinstance(profile, dict) or not PROFILE_REQUIRED.issubset(profile) or set(profile) - PROFILE_FIELDS:
        raise ValueError("invalid_profile")
    enums = {
        "task_kind": TASK_KINDS,
        "scope": {"single", "multi_module", "cross_system", "portfolio"},
        "risk": {"low", "moderate", "high", "irreversible"},
        "duration": {"short", "multi_stage", "long_running"},
        "priority": {"latency", "cost", "balanced", "quality_first", "max_quality"},
        "ambiguity": {"low", "medium", "high"},
        "verification_strength": {"weak", "partial", "strong"},
        "context_portability": {"self_contained", "workspace_recoverable", "thread_dependent"},
        "coupling": {"low", "medium", "high"},
        "write_conflict_risk": {"low", "medium", "high"},
    }
    for field, allowed in enums.items():
        if field in profile and profile[field] not in allowed:
            raise ValueError("invalid_profile")
    for field in ("architecture_signals", "repeated_failures", "parallel_workstreams"):
        if field in profile and (type(profile[field]) is not int or profile[field] < 0):
            raise ValueError("invalid_profile")
    for field in ("independently_verifiable", "delegation_authorized", "parallelism_observed", "single_hard_problem", "max_insufficient_evidence"):
        if field in profile and type(profile[field]) is not bool:
            raise ValueError("invalid_profile")


def recommend(payload: dict[str, Any]) -> dict[str, Any]:
    required_root = {"schema_version", "current", "profile", "catalog_evidence_status", "host_evidence_status", "host_models", "host_thinking", "host_role_models", "catalog_provenance", "host_provenance"}
    if not isinstance(payload, dict) or set(payload) != required_root or payload["schema_version"] != "1.0":
        raise ValueError("invalid_input_contract")
    current = payload["current"]
    profile = payload["profile"]
    if not isinstance(current, dict):
        raise ValueError("invalid_input_contract")
    required = {"evidence_status", "model", "effort", "observed_at"}
    if set(current) != required:
        raise ValueError("invalid_current_contract")
    evidence_values = {"verified", "stale", "unknown", "uncertain"}
    if current["effort"] not in CURRENT_EFFORTS or current["evidence_status"] not in evidence_values:
        raise ValueError("invalid_current_contract")
    if not isinstance(current["model"], str) or not MODEL_PATTERN.fullmatch(current["model"]):
        raise ValueError("invalid_current_contract")
    if current["observed_at"] is not None and not isinstance(current["observed_at"], str):
        raise ValueError("invalid_current_contract")
    if current["evidence_status"] == "verified" and not current["observed_at"]:
        raise ValueError("invalid_current_contract")
    if payload["catalog_evidence_status"] not in evidence_values or payload["host_evidence_status"] not in evidence_values:
        raise ValueError("invalid_evidence_status")
    if not isinstance(payload["host_models"], list) or len(payload["host_models"]) != len(set(payload["host_models"])) or any(not isinstance(value, str) or not MODEL_PATTERN.fullmatch(value) or value == "unknown" for value in payload["host_models"]):
        raise ValueError("invalid_host_capabilities")
    if not isinstance(payload["host_thinking"], list) or len(payload["host_thinking"]) != len(set(payload["host_thinking"])) or any(value not in EFFORTS for value in payload["host_thinking"]):
        raise ValueError("invalid_host_capabilities")
    role_models = payload["host_role_models"]
    if not isinstance(role_models, dict) or set(role_models) != {"throughput", "balanced", "deep"}:
        raise ValueError("invalid_host_capabilities")
    if any(value is not None and value not in payload["host_models"] for value in role_models.values()):
        raise ValueError("invalid_host_capabilities")
    catalog_payload = {"role_models": role_models, "observed_at": payload["catalog_provenance"]["observed_at"]}
    host_payload = {"models": sorted(payload["host_models"]), "thinking": sorted(payload["host_thinking"]), "role_models": role_models, "observed_at": payload["host_provenance"]["observed_at"]}
    catalog_valid = validate_provenance(payload["catalog_provenance"], "catalog", "catalog_observation", catalog_payload)
    host_valid = validate_provenance(payload["host_provenance"], "host_capability", "host_tool_schema", host_payload)
    validate_profile(profile)
    kind = profile["task_kind"]
    role = "deep" if kind in DEEP_KINDS or profile.get("risk") in {"high", "irreversible"} else "balanced"
    effort = {
        "simple_answer": "medium",
        "local_edit": "medium",
        "implementation": "high" if profile.get("duration") != "short" or profile.get("scope") != "single" else "medium",
        "architecture": "xhigh",
        "migration": "xhigh",
        "deep_research": "xhigh",
        "final_decision": "max",
        "batch": "low" if profile.get("priority") in {"latency", "cost"} else "medium",
    }[kind]
    parallel = (
        profile.get("delegation_authorized") is True
        and profile.get("parallelism_observed") is True
        and profile.get("parallel_workstreams", 0) >= 3
        and profile.get("coupling") == "low"
        and profile.get("independently_verifiable") is True
        and profile.get("write_conflict_risk") != "high"
    )
    topology = "parallel" if parallel else ("single_deep" if kind == "final_decision" else "single")
    supported = sorted(payload["host_thinking"], key=EFFORT_RANK.__getitem__)
    selected_effort = effort if effort in supported else next((value for value in supported if EFFORT_RANK[value] >= EFFORT_RANK[effort]), None)
    selected_model = role_models[role]
    resolved = selected_model is not None and selected_effort is not None
    try:
        current_fresh = current["evidence_status"] != "verified" or (
            parse_time(current["observed_at"]) <= datetime.now(timezone.utc) + timedelta(minutes=5)
            and datetime.now(timezone.utc) <= parse_time(current["observed_at"]) + timedelta(seconds=600)
        )
    except ValueError:
        current_fresh = False
    current_status = current["evidence_status"] if current_fresh else "unknown"
    catalog_status = payload["catalog_evidence_status"] if catalog_valid else "unknown"
    host_status = payload["host_evidence_status"] if host_valid else "unknown"
    combined_verified = all(value == "verified" for value in (current_status, catalog_status, host_status))
    benefit = "none"
    if resolved and combined_verified and current["effort"] in EFFORT_RANK and profile.get("duration") == "long_running" and EFFORT_RANK[current["effort"]] >= EFFORT_RANK[effort] + 2:
        benefit = "efficiency"
    decision = {
        "action": "stay",
        "benefit": benefit,
        "transfer": "none",
        "source_disposition": "keep",
        "evidence_status": current_status if combined_verified else max((current_status, catalog_status, host_status), key={"verified": 0, "stale": 1, "unknown": 2, "uncertain": 3}.__getitem__),
        "reason_code": "public_preview_recommendation_only",
    }
    recommended = {"model_role": role, "model": selected_model if resolved else None, "effort": selected_effort if resolved else None, "thinking": selected_effort if resolved else None, "topology": topology, "resolution": "resolved" if resolved else "unresolved"}
    current_role = next((candidate for candidate, candidate_model in role_models.items() if candidate_model == current["model"]), "unknown")
    status = "unknown"
    if combined_verified and resolved and current["effort"] != "unknown":
        status = "fit" if current_role == role and current["model"] == selected_model and current["effort"] == selected_effort and not parallel else "mismatch"
    return {
        "schema_version": "1.0",
        "status": status,
        "decision": decision,
        "current": {"model": current["model"], "model_role": current_role, "effort": current["effort"], "topology": "parallel" if profile.get("parallelism_observed") is True else "not_observed", "evidence_status": current_status},
        "recommended": recommended,
        "tool_overrides": {"model": recommended["model"], "thinking": recommended["thinking"]} if resolved else None,
        "effective_task_kind": kind,
        "reason_codes": ["public_preview_recommendation_only"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = recommend(json.loads(args.input_file.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
