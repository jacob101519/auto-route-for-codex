#!/usr/bin/env python3
"""Route a privacy-bounded task profile with capability-gated continuation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


BASE_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")
KNOWN_EFFORTS = BASE_EFFORTS + ("ultra",)
CURRENT_EFFORTS = ("unknown",) + KNOWN_EFFORTS
EFFORT_RANK = {value: index for index, value in enumerate(BASE_EFFORTS)}
MODEL_ROLES = ("throughput", "balanced", "deep")
MODEL_ROLE_RANK = {value: index for index, value in enumerate(MODEL_ROLES)}
DEEP_KINDS = {"architecture", "migration", "deep_research", "final_decision"}
QUALITY_CRITICAL_KINDS = DEEP_KINDS
TASK_KINDS = {"simple_answer", "local_edit", "implementation", *DEEP_KINDS, "batch"}
EVIDENCE_VALUES = {"verified", "stale", "unknown", "uncertain"}
EVIDENCE_ORDER = {"verified": 0, "stale": 1, "unknown": 2, "uncertain": 3}
HOST_SURFACES = {"codex_desktop", "codex_cli", "codex_ide", "codex_cloud", "unknown"}
REQUIRED_HOST_CAPABILITIES = (
    "source_task_context",
    "codex_app__fork_thread",
    "codex_app__send_message_to_thread",
    "codex_app__read_thread",
    "codex_app__navigate_to_codex_page",
    "codex_app__set_thread_archived",
)
PROFILE_FIELDS = {
    "task_kind", "scope", "risk", "duration", "priority", "ambiguity",
    "verification_strength", "context_portability", "architecture_signals",
    "repeated_failures", "parallel_workstreams", "coupling",
    "independently_verifiable", "write_conflict_risk", "delegation_authorized",
    "parallelism_observed", "single_hard_problem", "max_insufficient_evidence",
}
PROFILE_REQUIRED = {"task_kind", "scope", "risk", "duration", "priority"}
PROFILE_DEFAULTS: dict[str, Any] = {
    "ambiguity": "medium",
    "verification_strength": "partial",
    "context_portability": "workspace_recoverable",
    "architecture_signals": 0,
    "repeated_failures": 0,
    "parallel_workstreams": 1,
    "coupling": "high",
    "independently_verifiable": False,
    "write_conflict_risk": "medium",
    "delegation_authorized": False,
    "parallelism_observed": False,
    "single_hard_problem": False,
    "max_insufficient_evidence": False,
}
MODEL_PATTERN = re.compile(r"^(?:unknown|[A-Za-z0-9][A-Za-z0-9._+-]{0,127})$")
RECEIPT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MAX_TTL = {"current_setting": 600, "catalog": 604800, "host_capability": 600}


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("invalid_timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("invalid_timestamp")
    return parsed


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def validate_provenance(
    value: Any,
    kind: str,
    source: str | set[str],
    payload: dict[str, Any],
    *,
    now: datetime,
) -> bool:
    if value is None:
        return False
    keys = {
        "schema_version", "receipt_id", "evidence_kind", "source",
        "observed_at", "ttl_seconds", "content_sha256",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("invalid_provenance")
    allowed_sources = {source} if isinstance(source, str) else source
    if (
        value["schema_version"] != "1.0"
        or value["evidence_kind"] != kind
        or value["source"] not in allowed_sources
        or not isinstance(value["receipt_id"], str)
        or not RECEIPT_ID_PATTERN.fullmatch(value["receipt_id"])
        or type(value["ttl_seconds"]) is not int
        or not 1 <= value["ttl_seconds"] <= MAX_TTL[kind]
        or not isinstance(value["content_sha256"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", value["content_sha256"])
    ):
        raise ValueError("invalid_provenance")
    try:
        observed = parse_time(value["observed_at"])
    except ValueError:
        return False
    return (
        observed <= now + timedelta(minutes=5)
        and now <= observed + timedelta(seconds=value["ttl_seconds"])
        and value["content_sha256"] == canonical_sha256(payload)
    )


def validate_profile(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or not PROFILE_REQUIRED.issubset(value)
        or set(value) - PROFILE_FIELDS
    ):
        raise ValueError("invalid_profile")
    profile = {**PROFILE_DEFAULTS, **value}
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
        if profile[field] not in allowed:
            raise ValueError("invalid_profile")
    for field in ("architecture_signals", "repeated_failures", "parallel_workstreams"):
        if type(profile[field]) is not int or profile[field] < 0:
            raise ValueError("invalid_profile")
    for field in (
        "independently_verifiable", "delegation_authorized", "parallelism_observed",
        "single_hard_problem", "max_insufficient_evidence",
    ):
        if type(profile[field]) is not bool:
            raise ValueError("invalid_profile")
    return profile


def at_least(current: str, minimum: str) -> str:
    return minimum if EFFORT_RANK[current] < EFFORT_RANK[minimum] else current


def resolve_supported_effort(requested: str, supported: set[str]) -> tuple[str | None, str | None]:
    if requested in supported:
        return requested, None
    baseline = "max" if requested == "ultra" else requested
    for candidate in BASE_EFFORTS[EFFORT_RANK[baseline] :]:
        if candidate in supported:
            return candidate, "effort_adjusted_to_host_support"
    available = [value for value in BASE_EFFORTS if value in supported]
    if available:
        return available[-1], "effort_capped_by_host_support"
    return None, "host_has_no_supported_base_effort"


def effective_task_kind(profile: dict[str, Any]) -> tuple[str, list[str]]:
    kind = profile["task_kind"]
    reasons: list[str] = []
    if profile["architecture_signals"] >= 2 and kind not in {"migration", "deep_research", "final_decision"}:
        kind = "architecture"
        reasons.append("architecture_signal_override")
    return kind, reasons


def recommend_model_role(profile: dict[str, Any], kind: str) -> tuple[str, list[str]]:
    if kind in DEEP_KINDS:
        return "deep", ["deep_task_role"]
    if profile["risk"] in {"high", "irreversible"} or profile["ambiguity"] == "high":
        return "deep", ["risk_or_ambiguity_requires_deep_role"]
    if (
        kind == "batch"
        and profile["duration"] == "long_running"
        and profile["scope"] in {"single", "multi_module"}
        and profile["risk"] == "low"
        and profile["ambiguity"] == "low"
        and profile["verification_strength"] == "strong"
        and profile["priority"] in {"latency", "cost"}
    ):
        return "throughput", ["bounded_verified_high_volume_batch"]
    return "balanced", ["everyday_balanced_role"]


def resolve_model_role(
    requested_role: str,
    role_models: dict[str, str | None],
) -> tuple[str, str | None, list[str]]:
    start = MODEL_ROLE_RANK[requested_role]
    for role in MODEL_ROLES[start:]:
        model = role_models[role]
        if model is not None:
            reasons = [] if role == requested_role else ["model_role_adjusted_to_host_support"]
            return role, model, reasons
    return requested_role, None, ["host_has_no_model_for_required_role"]


def recommend_topology(profile: dict[str, Any], kind: str) -> tuple[str, list[str]]:
    reasons: list[str] = []
    parallel_shape = (
        kind in {"implementation", "architecture", "migration", "deep_research"}
        and profile["duration"] == "long_running"
        and profile["scope"] in {"cross_system", "portfolio"}
        and profile["priority"] in {"quality_first", "max_quality"}
        and profile["parallel_workstreams"] >= 3
    )
    if parallel_shape:
        if profile["coupling"] == "high":
            return "single_deep", ["parallelism_blocked_by_high_coupling"]
        if not profile["independently_verifiable"]:
            reasons.append("parallelism_blocked_by_shared_verification")
        elif profile["write_conflict_risk"] == "high":
            reasons.append("parallelism_blocked_by_write_conflict")
        else:
            return "parallel", ["meaningful_independent_parallel_workstreams"]
    if (
        profile["single_hard_problem"]
        or profile["max_insufficient_evidence"]
        or kind == "final_decision"
        or profile["risk"] == "irreversible"
    ):
        return "single_deep", [*reasons, "single_problem_requires_deep_continuity"]
    return "single", reasons


def recommend_effort(
    profile: dict[str, Any],
    kind: str,
    topology: str,
    supported: set[str],
) -> tuple[str | None, list[str]]:
    reasons = [f"task_kind:{kind}"]
    effort = {
        "simple_answer": "medium",
        "local_edit": "low" if profile["ambiguity"] == "low" and profile["verification_strength"] == "strong" else "medium",
        "implementation": "medium",
        "architecture": "xhigh",
        "migration": "xhigh",
        "deep_research": "xhigh",
        "final_decision": "max",
        "batch": "low" if profile["scope"] in {"single", "multi_module"} and profile["priority"] in {"latency", "cost"} else "medium",
    }[kind]
    if kind == "implementation" and (profile["scope"] != "single" or profile["duration"] != "short"):
        effort = at_least(effort, "high")
        reasons.append("multi_scope_or_multistage_implementation")
    if kind in {"simple_answer", "local_edit"} and profile["scope"] in {"cross_system", "portfolio"}:
        effort = at_least(effort, "high")
        reasons.append("cross_system_scope")
    if profile["ambiguity"] == "high":
        effort = at_least(effort, "high")
        reasons.append("high_ambiguity")
    if profile["verification_strength"] == "weak":
        effort = at_least(effort, "high")
        reasons.append("weak_verification")
    if profile["repeated_failures"] >= 3:
        effort = at_least(effort, "xhigh")
        reasons.append("three_or_more_related_failures")
    elif profile["repeated_failures"] >= 2:
        effort = at_least(effort, "high")
        reasons.append("two_related_failures")
    if profile["risk"] == "high":
        effort = at_least(effort, "xhigh")
        reasons.append("high_risk")
    elif profile["risk"] == "irreversible":
        effort = at_least(effort, "max")
        reasons.append("irreversible_risk")
    if profile["single_hard_problem"] or profile["max_insufficient_evidence"]:
        effort = at_least(effort, "max")
        reasons.append("single_problem_requires_maximum_depth")
    if profile["priority"] == "max_quality" and topology != "parallel" and EFFORT_RANK[effort] >= EFFORT_RANK["xhigh"]:
        effort = at_least(effort, "max")
        reasons.append("maximum_quality_priority")
    if topology == "parallel":
        if "ultra" in supported:
            effort = "ultra"
            reasons.append("ultra_combines_reasoning_and_delegation")
        else:
            effort = at_least(effort, "max")
            reasons.append("parallel_topology_without_host_ultra")
    resolved, support_reason = resolve_supported_effort(effort, supported)
    if support_reason:
        reasons.append(support_reason)
    return resolved, reasons


def role_for_model(role_models: dict[str, str | None], model: str) -> str | None:
    matches = [role for role in MODEL_ROLES if role_models[role] == model]
    return matches[-1] if matches else None


def compare_settings(
    profile: dict[str, Any],
    kind: str,
    current_model: str,
    current_effort: str,
    current_role: str | None,
    recommended_model: str,
    recommended_effort: str,
    recommended_role: str,
    recommended_topology: str,
) -> tuple[str, list[str]]:
    if current_model == "unknown" or current_effort == "unknown" or current_role is None:
        return "unknown", ["current_setting_unknown"]
    reasons: list[str] = []
    if current_model != recommended_model:
        if MODEL_ROLE_RANK[current_role] < MODEL_ROLE_RANK[recommended_role]:
            reasons.append("model_role_below_task_need")
        elif MODEL_ROLE_RANK[current_role] > MODEL_ROLE_RANK[recommended_role] and (profile["duration"] == "long_running" or kind == "batch"):
            reasons.append("model_role_materially_above_sustained_need")
        else:
            reasons.append("model_differs_from_recommended")
    if recommended_topology == "parallel":
        if not profile["parallelism_observed"]:
            reasons.append("parallelism_not_observed")
        if current_effort != recommended_effort:
            reasons.append("effort_below_task_need")
    elif current_effort == "ultra":
        reasons.append("automatic_parallelism_not_needed")
    else:
        current_rank = EFFORT_RANK[current_effort]
        recommended_rank = EFFORT_RANK[recommended_effort]
        if current_rank < recommended_rank:
            reasons.append("effort_below_task_need")
        elif current_rank - recommended_rank >= 2:
            reasons.append("effort_materially_above_task_need")
        elif current_effort == "max" and recommended_rank <= EFFORT_RANK["high"]:
            reasons.append("max_on_non_max_task")
    return ("mismatch", reasons) if reasons else ("fit", reasons)


def continuation_capable(surface: str, capabilities: dict[str, bool]) -> bool:
    return surface == "codex_desktop" and all(capabilities[name] for name in REQUIRED_HOST_CAPABILITIES)


def routing_decision(
    profile: dict[str, Any],
    kind: str,
    status: str,
    comparison_reasons: list[str],
    current_effort: str,
    recommended_effort: str,
    recommended_role: str,
    recommended_topology: str,
    evidence_status: str,
    host_can_continue: bool,
) -> dict[str, Any]:
    def stay(reason: str, benefit: str = "none") -> dict[str, Any]:
        return {
            "action": "stay", "benefit": benefit, "transfer": "none",
            "source_disposition": "keep", "evidence_status": evidence_status,
            "reason_code": reason,
        }

    def reroute(benefit: str, reason: str) -> dict[str, Any]:
        return {
            "action": "reroute", "benefit": benefit, "transfer": "fork",
            "source_disposition": "archive_after_continuation_ready",
            "evidence_status": evidence_status, "reason_code": reason,
        }

    if evidence_status != "verified" or status == "unknown":
        return stay("evidence_does_not_authorize_transfer")
    if status == "fit":
        return stay("current_setting_is_sufficient")
    if not host_can_continue:
        return stay("host_capability_gate_not_satisfied")
    reasons = set(comparison_reasons)
    if recommended_topology == "parallel":
        if not profile["parallelism_observed"] or "parallelism_not_observed" in reasons:
            return stay("parallelism_not_observed")
        if not profile["delegation_authorized"]:
            return stay("delegation_not_authorized")
        return reroute("parallelism", "independent_workstreams_benefit_from_parallelism")
    underpowered = bool(reasons & {"model_role_below_task_need", "model_differs_from_recommended", "effort_below_task_need"})
    if underpowered:
        effort_gap = 0
        if current_effort in EFFORT_RANK and recommended_effort in EFFORT_RANK:
            effort_gap = EFFORT_RANK[recommended_effort] - EFFORT_RANK[current_effort]
        critical = (
            kind in QUALITY_CRITICAL_KINDS
            or profile["risk"] in {"high", "irreversible"}
            or profile["repeated_failures"] >= 2
            or profile["single_hard_problem"]
            or profile["max_insufficient_evidence"]
        )
        if critical or recommended_role == "deep" or profile["duration"] != "short" or effort_gap >= 2:
            return reroute("quality", "current_setting_is_materially_underpowered")
        return stay("small_underpower_gap_does_not_justify_routing_overhead")
    overpowered = bool(reasons & {
        "model_role_materially_above_sustained_need", "effort_materially_above_task_need",
        "max_on_non_max_task", "automatic_parallelism_not_needed",
    })
    if overpowered:
        sustained = profile["duration"] == "long_running" or kind == "batch" or (profile["duration"] == "multi_stage" and current_effort == "ultra")
        if not sustained:
            return stay("one_off_savings_do_not_repay_routing_overhead")
        if profile["context_portability"] == "thread_dependent":
            return stay("history_copy_cost_cancels_efficiency_gain")
        return stay("efficiency_recommendation_requires_manual_choice", "efficiency")
    return stay("no_positive_net_value_for_new_thread")


def recommend(payload: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    required_root = {
        "schema_version", "current", "profile", "catalog_evidence_status",
        "host_evidence_status", "host_surface", "host_capabilities", "host_models",
        "host_thinking", "host_role_models", "current_provenance",
        "catalog_provenance", "host_provenance",
    }
    if not isinstance(payload, dict) or set(payload) != required_root or payload.get("schema_version") != "1.0":
        raise ValueError("invalid_input_contract")
    current = payload["current"]
    if not isinstance(current, dict) or set(current) != {"evidence_status", "model", "effort", "observed_at"}:
        raise ValueError("invalid_current_contract")
    if (
        current["evidence_status"] not in EVIDENCE_VALUES
        or current["effort"] not in CURRENT_EFFORTS
        or not isinstance(current["model"], str)
        or not MODEL_PATTERN.fullmatch(current["model"])
        or (current["observed_at"] is not None and not isinstance(current["observed_at"], str))
        or (current["evidence_status"] == "verified" and not current["observed_at"])
    ):
        raise ValueError("invalid_current_contract")
    if payload["catalog_evidence_status"] not in EVIDENCE_VALUES or payload["host_evidence_status"] not in EVIDENCE_VALUES:
        raise ValueError("invalid_evidence_status")
    if payload["host_surface"] not in HOST_SURFACES:
        raise ValueError("invalid_host_surface")
    capabilities = payload["host_capabilities"]
    if (
        not isinstance(capabilities, dict)
        or set(capabilities) != set(REQUIRED_HOST_CAPABILITIES)
        or any(type(value) is not bool for value in capabilities.values())
    ):
        raise ValueError("invalid_host_capabilities")
    host_models = payload["host_models"]
    host_thinking = payload["host_thinking"]
    if (
        not isinstance(host_models, list)
        or len(host_models) != len(set(host_models))
        or any(not isinstance(value, str) or not MODEL_PATTERN.fullmatch(value) or value == "unknown" for value in host_models)
        or not isinstance(host_thinking, list)
        or len(host_thinking) != len(set(host_thinking))
        or any(value not in KNOWN_EFFORTS for value in host_thinking)
    ):
        raise ValueError("invalid_host_capabilities")
    role_models = payload["host_role_models"]
    if not isinstance(role_models, dict) or set(role_models) != set(MODEL_ROLES):
        raise ValueError("invalid_host_capabilities")
    if any(value is not None and value not in host_models for value in role_models.values()):
        raise ValueError("invalid_host_capabilities")
    profile = validate_profile(payload["profile"])

    current_payload = {"model": current["model"], "effort": current["effort"], "observed_at": current["observed_at"]}
    catalog_observed_at = payload["catalog_provenance"].get("observed_at") if isinstance(payload["catalog_provenance"], dict) else None
    host_observed_at = payload["host_provenance"].get("observed_at") if isinstance(payload["host_provenance"], dict) else None
    catalog_payload = {"role_models": role_models, "observed_at": catalog_observed_at}
    host_payload = {
        "surface": payload["host_surface"],
        "capabilities": capabilities,
        "models": sorted(host_models),
        "thinking": sorted(host_thinking),
        "role_models": role_models,
        "observed_at": host_observed_at,
    }
    effective_now = now or _utc_now()
    if effective_now.tzinfo is None or effective_now.utcoffset() is None:
        raise ValueError("invalid_reference_time")
    effective_now = effective_now.astimezone(timezone.utc)
    current_valid = validate_provenance(
        payload["current_provenance"],
        "current_setting",
        {"host_current_setting", "local_session_turn_context"},
        current_payload,
        now=effective_now,
    )
    catalog_valid = validate_provenance(payload["catalog_provenance"], "catalog", "catalog_observation", catalog_payload, now=effective_now)
    host_valid = validate_provenance(payload["host_provenance"], "host_capability", "host_tool_schema", host_payload, now=effective_now)
    valid_receipts = [value for value, valid in (
        (payload["current_provenance"], current_valid),
        (payload["catalog_provenance"], catalog_valid),
        (payload["host_provenance"], host_valid),
    ) if valid]
    distinct_provenance = len(valid_receipts) == 3 and len({value["receipt_id"] for value in valid_receipts}) == 3
    current_status = current["evidence_status"]
    catalog_status = payload["catalog_evidence_status"]
    host_status = payload["host_evidence_status"]
    if current_status == "verified" and not current_valid:
        current_status = "uncertain"
    if catalog_status == "verified" and not catalog_valid:
        catalog_status = "uncertain"
    if host_status == "verified" and (not host_valid or not distinct_provenance):
        host_status = "uncertain"
    evidence_status = max((current_status, catalog_status, host_status), key=EVIDENCE_ORDER.__getitem__)

    kind, kind_reasons = effective_task_kind(profile)
    requested_role, role_reasons = recommend_model_role(profile, kind)
    role, model, resolution_reasons = resolve_model_role(requested_role, role_models)
    topology, topology_reasons = recommend_topology(profile, kind)
    effort, effort_reasons = recommend_effort(profile, kind, topology, set(host_thinking))
    resolved = model is not None and effort is not None
    current_role = role_for_model(role_models, current["model"])
    if resolved:
        status, comparison_reasons = compare_settings(
            profile, kind, current["model"], current["effort"], current_role,
            model, effort, role, topology,
        )
    else:
        status, comparison_reasons = "unknown", ["recommendation_unresolved"]
    if evidence_status != "verified":
        status = "unknown"
    host_can_continue = continuation_capable(payload["host_surface"], capabilities)
    decision = routing_decision(
        profile, kind, status, comparison_reasons, current["effort"], effort or "max",
        role, topology, evidence_status, host_can_continue,
    )
    reason_codes = list(dict.fromkeys(
        kind_reasons + role_reasons + resolution_reasons + topology_reasons
        + effort_reasons + comparison_reasons + [decision["reason_code"]]
    ))
    recommended = {
        "model_role": role,
        "model": model if resolved else None,
        "effort": effort if resolved else None,
        "thinking": effort if resolved else None,
        "topology": topology,
        "resolution": "resolved" if resolved else "unresolved",
    }
    tool_overrides = {"model": model, "thinking": effort} if resolved else None
    evidence = {
        "aggregate_status": evidence_status,
        "current": {
            "status": current_status,
            "provenance": (
                "session_turn_context_receipt"
                if current_valid and payload["current_provenance"]["source"] == "local_session_turn_context"
                else "host_setting_receipt"
                if current_valid
                else "unverified"
            ),
        },
        "catalog": {"status": catalog_status, "provenance": "integrity_receipt" if catalog_valid else "unverified"},
        "host": {"status": host_status, "provenance": "tool_schema_receipt" if host_valid else "unverified"},
        "continuation_capable": host_can_continue,
    }
    authorization_payload = {
        "decision": decision,
        "recommended": recommended,
        "current_provenance_sha256": canonical_sha256(payload["current_provenance"]) if current_valid else None,
        "catalog_provenance_sha256": canonical_sha256(payload["catalog_provenance"]) if catalog_valid else None,
        "host_provenance_sha256": canonical_sha256(payload["host_provenance"]) if host_valid else None,
        "host_surface": payload["host_surface"],
        "host_capabilities": capabilities,
    }
    return {
        "schema_version": "1.0",
        "status": status,
        "decision": decision,
        "current": {
            "model": current["model"],
            "model_role": current_role or "unknown",
            "effort": current["effort"],
            "topology": "parallel" if profile["parallelism_observed"] else "not_observed",
            "evidence_status": current_status,
        },
        "recommended": recommended,
        "tool_overrides": tool_overrides,
        "evidence": evidence,
        "route_authorization": canonical_sha256(authorization_payload),
        "effective_task_kind": kind,
        "reason_codes": reason_codes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = recommend(json.loads(args.input_file.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
