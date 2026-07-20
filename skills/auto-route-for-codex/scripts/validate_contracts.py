#!/usr/bin/env python3
"""Validate capability-gated public schemas and semantic invariants."""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError:  # Optional for dependency-free offline validation.
    Draft202012Validator = None

from route_task import REQUIRED_HOST_CAPABILITIES, canonical_sha256, recommend
from transfer_state import (
    _confirm_stateful_event as confirm_stateful_event,
    _create_stateful_receipt as create_stateful_receipt,
    _load_canonical_receipt as load_canonical_receipt,
    _read_state_file as read_state_file,
    _reservation_directory as reservation_directory,
    _reserve_stateful_event as reserve_stateful_event,
    _validate_receipt as validate_receipt,
)


ROOT = Path(__file__).resolve().parents[1] if (Path(__file__).resolve().parents[1] / "schemas").is_dir() else Path(__file__).resolve().parent
SCHEMAS = ROOT / "schemas" if (ROOT / "schemas").is_dir() else ROOT
FIXTURES = ROOT / "tests/fixtures/cases.json" if (ROOT / "tests/fixtures/cases.json").is_file() else ROOT / "tests/fixtures/cases.json"


def resolve(root: dict[str, Any], reference: str) -> dict[str, Any]:
    value: Any = root
    for part in reference[2:].split("/"):
        value = value[part]
    return value


def validate(value: Any, schema: dict[str, Any], root: dict[str, Any]) -> None:
    if "$ref" in schema:
        validate(value, resolve(root, schema["$ref"]), root)
        return
    if "type" in schema:
        choices = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        predicates = {"object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list), "string": lambda v: isinstance(v, str), "integer": lambda v: type(v) is int, "boolean": lambda v: type(v) is bool, "null": lambda v: v is None}
        if not any(predicates[item](value) for item in choices):
            raise ValueError("schema_type")
    if "const" in schema and value != schema["const"]:
        raise ValueError("schema_const")
    if "not" in schema:
        try:
            validate(value, schema["not"], root)
        except ValueError:
            pass
        else:
            raise ValueError("schema_not")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("schema_enum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 10**9) or ("pattern" in schema and not re.fullmatch(schema["pattern"], value)):
            raise ValueError("schema_string")
    if type(value) is int and (value < schema.get("minimum", value) or value > schema.get("maximum", value)):
        raise ValueError("schema_integer")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if not set(schema.get("required", [])).issubset(value) or (schema.get("additionalProperties") is False and set(value) - set(properties)):
            raise ValueError("schema_object")
        for key in value:
            if key in properties:
                validate(value[key], properties[key], root)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", 10**9):
            raise ValueError("schema_items")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            raise ValueError("schema_unique")
        for item in value:
            validate(item, schema.get("items", {}), root)
    for item in schema.get("allOf", []):
        validate(value, item, root)
    if "if" in schema:
        try:
            validate(value, schema["if"], root)
        except ValueError:
            pass
        else:
            if "then" in schema:
                validate(value, schema["then"], root)
    if "oneOf" in schema:
        matches = 0
        for item in schema["oneOf"]:
            try:
                validate(value, item, root)
            except ValueError:
                continue
            matches += 1
        if matches != 1:
            raise ValueError("schema_one_of")


def validate_contract(value: Any, schema: dict[str, Any]) -> None:
    validate(value, schema, schema)
    if Draft202012Validator is not None:
        Draft202012Validator(schema).validate(value)


def fresh(payload: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(payload)
    observed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if payload["current"]["evidence_status"] == "verified":
        payload["current"]["observed_at"] = observed
        payload["current_provenance"].update(observed_at=observed, ttl_seconds=600)
        payload["current_provenance"]["content_sha256"] = canonical_sha256({"model": payload["current"]["model"], "effort": payload["current"]["effort"], "observed_at": observed})
    payload["catalog_provenance"].update(observed_at=observed, ttl_seconds=604800)
    payload["catalog_provenance"]["content_sha256"] = canonical_sha256({"role_models": payload["host_role_models"], "observed_at": observed})
    payload["host_provenance"].update(observed_at=observed, ttl_seconds=600)
    payload["host_provenance"]["content_sha256"] = canonical_sha256({"surface": payload["host_surface"], "capabilities": payload["host_capabilities"], "models": sorted(payload["host_models"]), "thinking": sorted(payload["host_thinking"]), "role_models": payload["host_role_models"], "observed_at": observed})
    return payload


def main() -> int:
    input_schema = json.loads((SCHEMAS / "router-input.schema.json").read_text(encoding="utf-8"))
    output_schema = json.loads((SCHEMAS / "router-output.schema.json").read_text(encoding="utf-8"))
    transfer_schema = json.loads((SCHEMAS / "transfer-receipt.schema.json").read_text(encoding="utf-8"))
    reservation_schema = json.loads((SCHEMAS / "transfer-reservation.schema.json").read_text(encoding="utf-8"))
    if any(schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema" for schema in (input_schema, output_schema, transfer_schema, reservation_schema)):
        raise ValueError("wrong_schema_draft")
    if Draft202012Validator is not None:
        for schema in (input_schema, output_schema, transfer_schema, reservation_schema):
            Draft202012Validator.check_schema(schema)
    legal = {
        ("stay", "none", "none", "keep"),
        ("stay", "efficiency", "none", "keep"),
        ("reroute", "quality", "fork", "archive_after_continuation_ready"),
        ("reroute", "parallelism", "fork", "archive_after_continuation_ready"),
    }
    cases = json.loads(FIXTURES.read_text(encoding="utf-8"))
    for case in cases:
        payload = fresh(case["input"])
        validate_contract(payload, input_schema)
        result = recommend(payload)
        validate_contract(result, output_schema)
        decision = result["decision"]
        combination = tuple(decision[field] for field in ("action", "benefit", "transfer", "source_disposition"))
        if combination not in legal:
            raise ValueError("illegal_route_combination")
        if decision["transfer"] == "fork" and (decision["evidence_status"] != "verified" or not result["evidence"]["continuation_capable"]):
            raise ValueError("unauthorized_public_transfer")
        if result["recommended"]["resolution"] == "unresolved" and result["tool_overrides"] is not None:
            raise ValueError("unresolved_override_forbidden")
        if result["recommended"]["resolution"] == "resolved" and result["tool_overrides"] != {"model": result["recommended"]["model"], "thinking": result["recommended"]["thinking"]}:
            raise ValueError("resolved_override_mismatch")
        if decision["evidence_status"] != "verified" and combination != ("stay", "none", "none", "keep"):
            raise ValueError("nonverified_transfer_or_benefit_forbidden")
    invalid = fresh(cases[0]["input"])
    invalid["current"]["observed_at"] = None
    try:
        recommend(invalid)
    except ValueError:
        pass
    else:
        raise ValueError("verified_current_null_timestamp_accepted")

    semantic_negative_instances = 1
    for capability in REQUIRED_HOST_CAPABILITIES:
        payload = copy.deepcopy(cases[0]["input"])
        payload["host_capabilities"][capability] = False
        result = recommend(fresh(payload))
        if result["decision"]["transfer"] != "none":
            raise ValueError("missing_capability_authorized_transfer")
        semantic_negative_instances += 1
    payload = fresh(cases[0]["input"])
    payload["host_provenance"]["content_sha256"] = "0" * 64
    if recommend(payload)["decision"]["transfer"] != "none":
        raise ValueError("tampered_host_provenance_authorized_transfer")
    semantic_negative_instances += 1
    payload = copy.deepcopy(cases[0]["input"])
    payload["host_surface"] = "codex_cli"
    if recommend(fresh(payload))["decision"]["transfer"] != "none":
        raise ValueError("unsupported_surface_authorized_transfer")
    semantic_negative_instances += 1

    payload = copy.deepcopy(cases[2]["input"])
    payload["profile"]["parallelism_observed"] = False
    authorization_only = recommend(fresh(payload))["decision"]
    if (
        tuple(authorization_only[field] for field in ("action", "benefit", "transfer", "source_disposition"))
        != ("stay", "none", "none", "keep")
        or authorization_only["reason_code"] != "parallelism_not_observed"
    ):
        raise ValueError("delegation_substituted_for_parallelism_observation")
    semantic_negative_instances += 1

    payload = copy.deepcopy(cases[2]["input"])
    payload["profile"]["delegation_authorized"] = False
    observation_only = recommend(fresh(payload))["decision"]
    if (
        tuple(observation_only[field] for field in ("action", "benefit", "transfer", "source_disposition"))
        != ("stay", "none", "none", "keep")
        or observation_only["reason_code"] != "delegation_not_authorized"
    ):
        raise ValueError("parallelism_observation_substituted_for_delegation_authority")
    semantic_negative_instances += 1

    digest = "a" * 64
    router_input = fresh(cases[0]["input"])
    previous_state_home = os.environ.get("AUTO_ROUTE_STATE_HOME")
    previous_thread_id = os.environ.get("CODEX_THREAD_ID")
    with tempfile.TemporaryDirectory() as temporary:
        os.environ["AUTO_ROUTE_STATE_HOME"] = temporary
        os.environ["CODEX_THREAD_ID"] = "public-transfer-source"
        try:
            receipt = create_stateful_receipt("public-transfer-check", digest, router_input)
            validate_contract(receipt, transfer_schema)
            reservation = reserve_stateful_event(
                "public-transfer-check",
                "fork_created",
                router_input=router_input,
            )
            pending = load_canonical_receipt(reservation_directory())
            validate_contract(pending, transfer_schema)
            mismatched_pending = copy.deepcopy(pending)
            mismatched_pending["pending_reservation"]["event"] = "navigation_confirmed"
            try:
                validate_contract(mismatched_pending, transfer_schema)
            except ValueError:
                pass
            else:
                raise ValueError("schema_accepted_mismatched_pending_event")
            semantic_negative_instances += 1
            validate_contract(
                read_state_file(reservation_directory() / "fork_created.json"),
                reservation_schema,
            )
            receipt = confirm_stateful_event(
                "public-transfer-check",
                "fork_created",
                "destination-check",
                router_input=router_input,
                reservation_lease=reservation["reservation_lease"],
            )
            reservation = reserve_stateful_event(
                "public-transfer-check",
                "prompt_delivery_confirmed",
                "destination-check",
                digest,
                router_input=router_input,
                observed_model=receipt["recommended_model"],
                observed_thinking=receipt["recommended_thinking"],
            )
            receipt = confirm_stateful_event(
                "public-transfer-check",
                "prompt_delivery_confirmed",
                "destination-check",
                digest,
                router_input=router_input,
                reservation_lease=reservation["reservation_lease"],
                observed_model=receipt["recommended_model"],
                observed_thinking=receipt["recommended_thinking"],
            )
            uncertain = confirm_stateful_event(
                "public-transfer-check",
                "timeout",
                router_input=router_input,
            )
            validate_contract(uncertain, transfer_schema)
            if uncertain["archive_authorized"]:
                raise ValueError("uncertain_transfer_authorized_archive")
            semantic_negative_instances += 1

            os.environ["CODEX_THREAD_ID"] = "forged-transfer-source"
            ready = create_stateful_receipt("forged-transfer", digest, router_input)
            for event in (
                "fork_created",
                "prompt_delivery_confirmed",
                "destination_readback_confirmed",
                "navigation_confirmed",
            ):
                destination = None if event == "fork_created" else "destination-check"
                event_digest = digest if event in {"prompt_delivery_confirmed", "destination_readback_confirmed"} else None
                event_model = ready["recommended_model"] if event == "prompt_delivery_confirmed" else None
                event_thinking = ready["recommended_thinking"] if event == "prompt_delivery_confirmed" else None
                reservation = reserve_stateful_event(
                    "forged-transfer",
                    event,
                    destination,
                    event_digest,
                    router_input=router_input,
                    observed_model=event_model,
                    observed_thinking=event_thinking,
                )
                ready = confirm_stateful_event(
                    "forged-transfer",
                    event,
                    "destination-check",
                    event_digest,
                    router_input=router_input,
                    reservation_lease=reservation["reservation_lease"],
                    observed_model=event_model,
                    observed_thinking=event_thinking,
                )
        finally:
            if previous_state_home is None:
                os.environ.pop("AUTO_ROUTE_STATE_HOME", None)
            else:
                os.environ["AUTO_ROUTE_STATE_HOME"] = previous_state_home
            if previous_thread_id is None:
                os.environ.pop("CODEX_THREAD_ID", None)
            else:
                os.environ["CODEX_THREAD_ID"] = previous_thread_id
    forged = copy.deepcopy(ready)
    forged["route_authorization"] = "b" * 64
    validate_contract(forged, transfer_schema)
    try:
        validate_receipt(
            forged,
            router_input,
            source_binding_sha256=forged["source_binding_sha256"],
        )
    except ValueError:
        pass
    else:
        raise ValueError("forged_archive_state_passed_reducer_validation")
    semantic_negative_instances += 1
    forged_source = copy.deepcopy(ready)
    forged_source["source_binding_sha256"] = "b" * 64
    validate_contract(forged_source, transfer_schema)
    try:
        validate_receipt(
            forged_source,
            router_input,
            source_binding_sha256=ready["source_binding_sha256"],
        )
    except ValueError:
        pass
    else:
        raise ValueError("forged_source_binding_passed_reducer_validation")
    semantic_negative_instances += 1
    print(json.dumps({
        "status": "pass",
        "schema_engine": "draft2020-12" if Draft202012Validator is not None else "stdlib_fallback",
        "schemas": 4,
        "instances": len(cases),
        "semantic_negative_instances": semantic_negative_instances,
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
