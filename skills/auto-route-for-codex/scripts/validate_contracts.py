#!/usr/bin/env python3
"""Validate public recommendation-only schemas and semantic invariants."""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from route_task import canonical_sha256, recommend


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


def fresh(payload: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(payload)
    observed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if payload["current"]["evidence_status"] == "verified":
        payload["current"]["observed_at"] = observed
    payload["catalog_provenance"].update(observed_at=observed, ttl_seconds=604800)
    payload["catalog_provenance"]["content_sha256"] = canonical_sha256({"role_models": payload["host_role_models"], "observed_at": observed})
    payload["host_provenance"].update(observed_at=observed, ttl_seconds=600)
    payload["host_provenance"]["content_sha256"] = canonical_sha256({"models": sorted(payload["host_models"]), "thinking": sorted(payload["host_thinking"]), "role_models": payload["host_role_models"], "observed_at": observed})
    return payload


def main() -> int:
    input_schema = json.loads((SCHEMAS / "router-input.schema.json").read_text(encoding="utf-8"))
    output_schema = json.loads((SCHEMAS / "router-output.schema.json").read_text(encoding="utf-8"))
    if input_schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema" or output_schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ValueError("wrong_schema_draft")
    decision_schema = output_schema["properties"]["decision"]["properties"]
    if (decision_schema["action"].get("const"), decision_schema["transfer"].get("const"), decision_schema["source_disposition"].get("const")) != ("stay", "none", "keep"):
        raise ValueError("public_output_not_recommendation_only")
    cases = json.loads(FIXTURES.read_text(encoding="utf-8"))
    for case in cases:
        payload = fresh(case["input"])
        validate(payload, input_schema, input_schema)
        result = recommend(payload)
        validate(result, output_schema, output_schema)
        if result["decision"]["action"] != "stay" or result["decision"]["transfer"] != "none" or result["decision"]["source_disposition"] != "keep":
            raise ValueError("public_transfer_forbidden")
        if result["recommended"]["resolution"] == "unresolved" and result["tool_overrides"] is not None:
            raise ValueError("unresolved_override_forbidden")
        if result["recommended"]["resolution"] == "resolved" and result["tool_overrides"] != {"model": result["recommended"]["model"], "thinking": result["recommended"]["thinking"]}:
            raise ValueError("resolved_override_mismatch")
        if result["decision"]["evidence_status"] != "verified" and result["decision"]["benefit"] != "none":
            raise ValueError("nonverified_public_benefit_forbidden")
    invalid = fresh(cases[0]["input"])
    invalid["current"]["observed_at"] = None
    try:
        recommend(invalid)
    except ValueError:
        pass
    else:
        raise ValueError("verified_current_null_timestamp_accepted")
    print(json.dumps({"status": "pass", "schemas": 2, "instances": len(cases), "semantic_negative_instances": 3}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
