from __future__ import annotations

import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "scripts" if (ROOT / "scripts" / "route_task.py").is_file() else ROOT
sys.path.insert(0, str(SOURCE_PATH))
from route_task import canonical_sha256, recommend  # noqa: E402


def fresh(value: dict) -> dict:
    value = json.loads(json.dumps(value))
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if value["current"]["evidence_status"] == "verified":
        value["current"]["observed_at"] = observed_at
    value["catalog_provenance"]["observed_at"] = observed_at
    value["catalog_provenance"]["ttl_seconds"] = 604800
    value["catalog_provenance"]["content_sha256"] = canonical_sha256({"role_models": value["host_role_models"], "observed_at": observed_at})
    value["host_provenance"]["observed_at"] = observed_at
    value["host_provenance"]["ttl_seconds"] = 600
    value["host_provenance"]["content_sha256"] = canonical_sha256({"models": sorted(value["host_models"]), "thinking": sorted(value["host_thinking"]), "role_models": value["host_role_models"], "observed_at": observed_at})
    return value


class PublicRecommendationTests(unittest.TestCase):
    def test_fixtures_are_deterministic_and_never_transfer(self) -> None:
        cases = json.loads((Path(__file__).parent / "fixtures" / "cases.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case=case["name"]):
                payload = fresh(case["input"])
                first = recommend(payload)
                second = recommend(payload)
                self.assertEqual(first, second)
                for field in ("model_role", "model", "thinking", "topology", "resolution"):
                    self.assertEqual(first["recommended"][field], case["expected"][field])
                self.assertEqual(first["decision"]["action"], "stay")
                self.assertEqual(first["decision"]["transfer"], "none")
                self.assertEqual(first["decision"]["source_disposition"], "keep")
                self.assertEqual(first["decision"]["benefit"], case["expected"]["benefit"])
                if first["recommended"]["resolution"] == "resolved":
                    self.assertIn(first["recommended"]["model"], payload["host_models"])
                    self.assertIn(first["recommended"]["thinking"], payload["host_thinking"])
                    self.assertEqual(first["tool_overrides"], {"model": first["recommended"]["model"], "thinking": first["recommended"]["thinking"]})
                else:
                    self.assertIsNone(first["tool_overrides"])

    def test_strict_root_contract(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_input_contract"):
            recommend({"schema_version": "1.0", "current": {}, "profile": {}, "extra": True})

    def test_missing_invalid_and_extra_profile_fields_are_rejected(self) -> None:
        case = fresh(json.loads((Path(__file__).parent / "fixtures" / "cases.json").read_text(encoding="utf-8"))[0]["input"])
        for mutate in (
            lambda value: value["profile"].pop("scope"),
            lambda value: value["profile"].update(scope="invalid"),
            lambda value: value["profile"].update(extra=True),
        ):
            value = json.loads(json.dumps(case))
            mutate(value)
            with self.assertRaisesRegex(ValueError, "invalid_profile"):
                recommend(value)

    def test_invalid_current_and_host_values_are_rejected(self) -> None:
        case = fresh(json.loads((Path(__file__).parent / "fixtures" / "cases.json").read_text(encoding="utf-8"))[0]["input"])
        variants = []
        missing = json.loads(json.dumps(case))
        missing["current"].pop("model")
        variants.append(missing)
        invalid_effort = json.loads(json.dumps(case))
        invalid_effort["current"]["effort"] = "invalid"
        variants.append(invalid_effort)
        extra = json.loads(json.dumps(case))
        extra["current"]["extra"] = True
        variants.append(extra)
        duplicate_host = json.loads(json.dumps(case))
        duplicate_host["host_models"].append(duplicate_host["host_models"][0])
        variants.append(duplicate_host)
        for index, value in enumerate(variants):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    recommend(value)

    def test_unresolved_recommendation_has_no_tool_overrides(self) -> None:
        case = fresh(json.loads((Path(__file__).parent / "fixtures/cases.json").read_text(encoding="utf-8"))[0]["input"])
        case["host_role_models"]["deep"] = None
        result = recommend(case)
        self.assertEqual(result["recommended"]["resolution"], "unresolved")
        self.assertIsNone(result["recommended"]["model"])
        self.assertIsNone(result["recommended"]["thinking"])
        self.assertIsNone(result["tool_overrides"])
        self.assertEqual(result["decision"]["benefit"], "none")
        self.assertEqual(result["status"], "unknown")

    def test_stale_future_or_unbound_provenance_downgrades_to_unknown(self) -> None:
        case = fresh(json.loads((Path(__file__).parent / "fixtures/cases.json").read_text(encoding="utf-8"))[0]["input"])
        variants = []
        stale = json.loads(json.dumps(case))
        stale["host_provenance"]["observed_at"] = "2000-01-01T00:00:00Z"
        variants.append(stale)
        future = json.loads(json.dumps(case))
        future["host_provenance"]["observed_at"] = "2999-01-01T00:00:00Z"
        variants.append(future)
        unbound = json.loads(json.dumps(case))
        unbound["host_provenance"]["content_sha256"] = "a" * 64
        variants.append(unbound)
        for value in variants:
            result = recommend(value)
            self.assertEqual(result["status"], "unknown")
            self.assertNotEqual(result["decision"]["evidence_status"], "verified")
            self.assertEqual(result["decision"]["benefit"], "none")

    def test_parallel_topology_requires_permission_observation_and_shape(self) -> None:
        case = fresh(json.loads((Path(__file__).parent / "fixtures/cases.json").read_text(encoding="utf-8"))[0]["input"])
        case["profile"].update(parallel_workstreams=4, coupling="low", independently_verifiable=True, write_conflict_risk="low", delegation_authorized=False, parallelism_observed=False)
        self.assertNotEqual(recommend(case)["recommended"]["topology"], "parallel")
        case["profile"]["delegation_authorized"] = True
        self.assertNotEqual(recommend(case)["recommended"]["topology"], "parallel")
        case["profile"]["parallelism_observed"] = True
        self.assertEqual(recommend(case)["recommended"]["topology"], "parallel")

    def test_public_output_contract_is_recommendation_only(self) -> None:
        schema_root = ROOT / "schemas" if (ROOT / "schemas").is_dir() else ROOT
        schema = json.loads((schema_root / "router-output.schema.json").read_text(encoding="utf-8"))
        decision = schema["properties"]["decision"]["properties"]
        self.assertEqual(decision["action"], {"const": "stay"})
        self.assertEqual(decision["transfer"], {"const": "none"})
        self.assertEqual(decision["source_disposition"], {"const": "keep"})

    def test_public_contract_validator_passes(self) -> None:
        script = ROOT / "scripts/validate_contracts.py" if (ROOT / "scripts/validate_contracts.py").is_file() else ROOT / "validate_contracts.py"
        completed = subprocess.run([sys.executable, str(script)], check=False, capture_output=True, text=True)
        self.assertEqual((completed.returncode, completed.stderr), (0, ""), completed.stdout + completed.stderr)
        self.assertEqual(json.loads(completed.stdout), {"status": "pass", "schemas": 2, "instances": 3, "semantic_negative_instances": 3})


if __name__ == "__main__":
    unittest.main()
