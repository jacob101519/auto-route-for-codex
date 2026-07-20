from __future__ import annotations

import copy
import importlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" if (ROOT / "scripts" / "transfer_state.py").is_file() else ROOT
sys.path.insert(0, str(SCRIPTS))

from route_task import canonical_sha256  # noqa: E402
from transfer_state import (  # noqa: E402
    CONFIRMED_STATES,
    _atomic_write_receipt as atomic_write_receipt,
    _confirm_stateful_event as confirm_stateful_event,
    _confirmed_state_chain as confirmed_state_chain,
    _create_stateful_receipt as create_stateful_receipt,
    _expected_state_chain as expected_state_chain,
    _load_canonical_receipt as load_canonical_receipt,
    _mark_uncertain as mark_uncertain,
    _new_receipt as new_receipt,
    _reservation_directory as reservation_directory,
    _reservation_payload as reservation_payload,
    _reserve_stateful_event as reserve_stateful_event,
    _source_binding_sha256 as source_binding_sha256,
    _validate_receipt as validate_receipt,
    _write_reservation as write_reservation,
)


FIXTURES = Path(__file__).parent / "fixtures" / "cases.json"


def fresh_router_input(index: int = 0) -> dict:
    payload = copy.deepcopy(json.loads(FIXTURES.read_text(encoding="utf-8"))[index]["input"])
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if payload["current"]["evidence_status"] == "verified":
        payload["current"]["observed_at"] = observed_at
        payload["current_provenance"].update(observed_at=observed_at, ttl_seconds=600)
        payload["current_provenance"]["content_sha256"] = canonical_sha256({
            "model": payload["current"]["model"],
            "effort": payload["current"]["effort"],
            "observed_at": observed_at,
        })
    payload["catalog_provenance"].update(observed_at=observed_at, ttl_seconds=604800)
    payload["catalog_provenance"]["content_sha256"] = canonical_sha256({
        "role_models": payload["host_role_models"],
        "observed_at": observed_at,
    })
    payload["host_provenance"].update(observed_at=observed_at, ttl_seconds=600)
    payload["host_provenance"]["content_sha256"] = canonical_sha256({
        "surface": payload["host_surface"],
        "capabilities": payload["host_capabilities"],
        "models": sorted(payload["host_models"]),
        "thinking": sorted(payload["host_thinking"]),
        "role_models": payload["host_role_models"],
        "observed_at": observed_at,
    })
    return payload


ROUTER_INPUT = fresh_router_input()


class TransferStateTests(unittest.TestCase):
    DIGEST = "a" * 64
    DESTINATION = "destination-test"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.previous_state_home = os.environ.get("AUTO_ROUTE_STATE_HOME")
        self.previous_thread_id = os.environ.get("CODEX_THREAD_ID")
        os.environ["AUTO_ROUTE_STATE_HOME"] = self.temporary.name
        os.environ["CODEX_THREAD_ID"] = "source-default"

    def tearDown(self) -> None:
        if self.previous_state_home is None:
            os.environ.pop("AUTO_ROUTE_STATE_HOME", None)
        else:
            os.environ["AUTO_ROUTE_STATE_HOME"] = self.previous_state_home
        if self.previous_thread_id is None:
            os.environ.pop("CODEX_THREAD_ID", None)
        else:
            os.environ["CODEX_THREAD_ID"] = self.previous_thread_id
        self.temporary.cleanup()

    def set_source(self, source_id: str) -> None:
        os.environ["CODEX_THREAD_ID"] = source_id

    def start(self, transfer_id: str, *, source_id: str | None = None) -> dict:
        self.set_source(source_id or f"source-{transfer_id}")
        return create_stateful_receipt(transfer_id, self.DIGEST, ROUTER_INPUT)

    def arguments(self, receipt: dict, event: str) -> tuple[dict, dict]:
        reserve: dict = {"router_input": ROUTER_INPUT}
        confirm: dict = {"router_input": ROUTER_INPUT}
        if event != "fork_created":
            reserve["destination_thread_id"] = receipt["destination_thread_id"]
            confirm["destination_thread_id"] = receipt["destination_thread_id"]
        else:
            confirm["destination_thread_id"] = self.DESTINATION
        if event in {"prompt_delivery_confirmed", "destination_readback_confirmed"}:
            reserve["prompt_sha256"] = self.DIGEST
            confirm["prompt_sha256"] = self.DIGEST
        if event == "prompt_delivery_confirmed":
            reserve["observed_model"] = receipt["recommended_model"]
            reserve["observed_thinking"] = receipt["recommended_thinking"]
            confirm["observed_model"] = receipt["recommended_model"]
            confirm["observed_thinking"] = receipt["recommended_thinking"]
        return reserve, confirm

    def advance(self, receipt: dict, event: str) -> dict:
        reserve_args, confirm_args = self.arguments(receipt, event)
        reservation = reserve_stateful_event(receipt["transfer_id"], event, **reserve_args)
        self.assertTrue(reservation["side_effect_authorized"])
        return confirm_stateful_event(
            receipt["transfer_id"],
            event,
            reservation_lease=reservation["reservation_lease"],
            **confirm_args,
        )

    def test_full_confirmed_sequence_and_archive_boundary(self) -> None:
        receipt = self.start("transfer-full")
        for event in CONFIRMED_STATES[:3]:
            receipt = self.advance(receipt, event)
        self.assertFalse(receipt["archive_authorized"])
        receipt = self.advance(receipt, "navigation_confirmed")
        self.assertTrue(receipt["archive_authorized"])
        receipt = self.advance(receipt, "source_archive_confirmed")
        self.assertEqual(receipt["state"], "source_archive_confirmed")
        self.assertFalse(receipt["archive_authorized"])
        self.assertIsNone(receipt["pending_reservation"])
        validate_receipt(receipt, ROUTER_INPUT)

    def test_receipt_requires_a_recomputed_authorized_route(self) -> None:
        for fixture_index in (1, 3, 4, 5, 6):
            with self.subTest(fixture_index=fixture_index):
                with self.assertRaisesRegex(ValueError, "route_not_authorized"):
                    new_receipt(
                        f"transfer-rejected-{fixture_index}",
                        self.DIGEST,
                        fresh_router_input(fixture_index),
                    )
        tampered = fresh_router_input()
        tampered["current_provenance"]["content_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "route_not_authorized"):
            new_receipt("transfer-rejected-tampered", self.DIGEST, tampered)

    def test_authorization_and_pending_bindings_reject_mutation(self) -> None:
        receipt = self.start("transfer-binding")
        reservation = reserve_stateful_event("transfer-binding", "fork_created", router_input=ROUTER_INPUT)
        receipt = load_canonical_receipt(reservation_directory())
        validate_receipt(receipt, ROUTER_INPUT)
        mutations = (
            ("transfer_id", "different-transfer"),
            ("source_binding_sha256", "b" * 64),
            ("prompt_sha256", "b" * 64),
            ("router_input_sha256", "b" * 64),
            ("route_authorization", "0" * 64),
            ("authorization_binding", "0" * 64),
            ("recommended_model", "different-model"),
            ("recommended_thinking", "low"),
            ("state_chain_sha256", "0" * 64),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                forged = copy.deepcopy(receipt)
                forged[field] = value
                with self.assertRaises(ValueError):
                    validate_receipt(forged, ROUTER_INPUT)
        forged_pending = copy.deepcopy(receipt)
        forged_pending["pending_reservation"]["lease_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_receipt(forged_pending, ROUTER_INPUT)

    def test_default_state_root_is_durable_codex_home(self) -> None:
        os.environ.pop("AUTO_ROUTE_STATE_HOME", None)
        previous_codex_home = os.environ.get("CODEX_HOME")
        with tempfile.TemporaryDirectory() as codex_home:
            os.environ["CODEX_HOME"] = codex_home
            try:
                self.start("transfer-default-root")
                reservation = reserve_stateful_event(
                    "transfer-default-root",
                    "fork_created",
                    router_input=ROUTER_INPUT,
                )
                expected = Path(codex_home) / "state" / "auto-route-for-codex"
                self.assertTrue(reservation["side_effect_authorized"])
                self.assertTrue(expected.is_dir())
                self.assertEqual(stat.S_IMODE(expected.stat().st_mode), 0o700)
                self.assertTrue(any(expected.rglob("fork_created.json")))
            finally:
                if previous_codex_home is None:
                    os.environ.pop("CODEX_HOME", None)
                else:
                    os.environ["CODEX_HOME"] = previous_codex_home
        os.environ["AUTO_ROUTE_STATE_HOME"] = self.temporary.name

    def test_concurrent_reservation_has_exactly_one_winner(self) -> None:
        self.start("transfer-concurrent")
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(
                lambda _: reserve_stateful_event(
                    "transfer-concurrent",
                    "fork_created",
                    router_input=ROUTER_INPUT,
                ),
                range(32),
            ))
        self.assertEqual(sum(result["side_effect_authorized"] for result in results), 1)
        self.assertEqual(sum(result["status"] == "reconcile_required" for result in results), 31)

    def test_same_source_different_transfer_ids_have_one_binding(self) -> None:
        self.set_source("source-one-binding")

        def create(transfer_id: str) -> dict | str:
            try:
                return create_stateful_receipt(transfer_id, self.DIGEST, ROUTER_INPUT)
            except ValueError as exc:
                return str(exc)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(create, ("same-source-a", "same-source-b")))
        receipts = [result for result in results if isinstance(result, dict)]
        errors = [result for result in results if isinstance(result, str)]
        self.assertEqual(len(receipts), 1)
        self.assertEqual(errors, ["source_task_already_bound"])
        self.assertEqual(receipts[0]["source_binding_sha256"], source_binding_sha256())

        reservation = reserve_stateful_event(
            receipts[0]["transfer_id"],
            "fork_created",
            router_input=ROUTER_INPUT,
        )
        self.assertTrue(reservation["side_effect_authorized"])

    def test_wrong_source_cannot_resume_or_archive_bound_transfer(self) -> None:
        receipt = self.start("transfer-source-bound", source_id="source-bound-a")
        for event in CONFIRMED_STATES[:4]:
            receipt = self.advance(receipt, event)
        self.assertTrue(receipt["archive_authorized"])

        self.set_source("source-bound-b")
        with self.assertRaisesRegex(ValueError, "state_file_missing"):
            reserve_stateful_event(
                receipt["transfer_id"],
                "source_archive_confirmed",
                destination_thread_id=receipt["destination_thread_id"],
                router_input=ROUTER_INPUT,
            )
        with self.assertRaisesRegex(ValueError, "state_file_missing"):
            confirm_stateful_event(
                receipt["transfer_id"],
                "source_archive_confirmed",
                destination_thread_id=receipt["destination_thread_id"],
                router_input=ROUTER_INPUT,
                reservation_lease="0" * 64,
            )

        self.set_source("source-bound-a")
        winner = reserve_stateful_event(
            receipt["transfer_id"],
            "source_archive_confirmed",
            destination_thread_id=receipt["destination_thread_id"],
            router_input=ROUTER_INPUT,
        )
        self.assertTrue(winner["side_effect_authorized"])

    def test_source_context_is_required_and_raw_id_is_not_persisted(self) -> None:
        self.set_source("source-private-binding")
        receipt = create_stateful_receipt("transfer-private-binding", self.DIGEST, ROUTER_INPUT)
        serialized = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("source-private-binding", serialized)
        self.assertEqual(receipt["source_binding_sha256"], source_binding_sha256())
        reserve_stateful_event(
            "transfer-private-binding",
            "fork_created",
            router_input=ROUTER_INPUT,
        )
        marker_text = (reservation_directory() / "fork_created.json").read_text(encoding="ascii")
        self.assertNotIn("source-private-binding", marker_text)
        self.assertIn(receipt["source_binding_sha256"], marker_text)

        os.environ.pop("CODEX_THREAD_ID")
        with self.assertRaisesRegex(ValueError, "source_thread_context_required"):
            create_stateful_receipt("transfer-missing-source", self.DIGEST, ROUTER_INPUT)

    def test_interprocess_flock_has_exactly_one_cli_winner(self) -> None:
        self.start("transfer-process-concurrent")
        router_input_path = Path(self.temporary.name) / "process-router-input.json"
        router_input_path.write_text(json.dumps(ROUTER_INPUT), encoding="utf-8")
        command = [
            sys.executable,
            str(SCRIPTS / "transfer_state.py"),
            "--router-input",
            str(router_input_path),
            "--transfer-id",
            "transfer-process-concurrent",
            "--reserve-event",
            "fork_created",
        ]

        def run_process(_: int) -> dict:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                env=dict(os.environ),
            )
            return json.loads(completed.stdout)

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(run_process, range(16)))
        self.assertEqual(sum(result["side_effect_authorized"] for result in results), 1)
        self.assertEqual(sum(result["status"] == "reconcile_required" for result in results), 15)

    def test_pending_receipt_prevents_reauthorization_when_marker_is_missing(self) -> None:
        self.start("transfer-marker-loss")
        winner = reserve_stateful_event("transfer-marker-loss", "fork_created", router_input=ROUTER_INPUT)
        directory = reservation_directory()
        (directory / "fork_created.json").unlink()
        retry = reserve_stateful_event("transfer-marker-loss", "fork_created", router_input=ROUTER_INPUT)
        self.assertTrue(winner["side_effect_authorized"])
        self.assertEqual(
            (retry["status"], retry["side_effect_authorized"], retry["reason"]),
            ("reconcile_required", False, "canonical_reservation_pending"),
        )
        with self.assertRaisesRegex(ValueError, "state_file_missing"):
            confirm_stateful_event(
                "transfer-marker-loss",
                "fork_created",
                self.DESTINATION,
                router_input=ROUTER_INPUT,
                reservation_lease=winner["reservation_lease"],
            )
        persisted = load_canonical_receipt(directory)
        self.assertEqual(persisted["pending_reservation"]["event"], "fork_created")

    def test_orphaned_marker_without_pending_receipt_requires_reconciliation(self) -> None:
        receipt = self.start("transfer-orphan-marker")
        directory = reservation_directory()
        lease_hash = canonical_sha256({"reservation_lease": "f" * 64})
        marker = reservation_payload(
            receipt,
            "fork_created",
            None,
            None,
            None,
            None,
            lease_sha256=lease_hash,
        )
        self.assertTrue(write_reservation(directory / "fork_created.json", marker))
        retry = reserve_stateful_event("transfer-orphan-marker", "fork_created", router_input=ROUTER_INPUT)
        self.assertEqual((retry["status"], retry["side_effect_authorized"]), ("reconcile_required", False))

    def test_only_winner_lease_can_confirm(self) -> None:
        self.start("transfer-lease")
        winner = reserve_stateful_event("transfer-lease", "fork_created", router_input=ROUTER_INPUT)
        loser = reserve_stateful_event("transfer-lease", "fork_created", router_input=ROUTER_INPUT)
        self.assertFalse(loser["side_effect_authorized"])
        for lease, error in ((None, "reservation_lease_required"), ("0" * 64, "reservation_lease_mismatch")):
            with self.subTest(error=error):
                with self.assertRaisesRegex(ValueError, error):
                    confirm_stateful_event(
                        "transfer-lease",
                        "fork_created",
                        "destination-by-loser",
                        router_input=ROUTER_INPUT,
                        reservation_lease=lease,
                    )
        pending = load_canonical_receipt(reservation_directory())
        self.assertEqual((pending["state"], pending["destination_thread_id"]), ("planned", None))
        confirmed = confirm_stateful_event(
            "transfer-lease",
            "fork_created",
            self.DESTINATION,
            router_input=ROUTER_INPUT,
            reservation_lease=winner["reservation_lease"],
        )
        self.assertEqual((confirmed["state"], confirmed["destination_thread_id"]), ("fork_created", self.DESTINATION))

    def test_stateful_store_is_monotonic_idempotent_and_transfer_bound(self) -> None:
        planned = self.start("transfer-stateful")
        reservation = reserve_stateful_event("transfer-stateful", "fork_created", router_input=ROUTER_INPUT)
        forked = confirm_stateful_event(
            "transfer-stateful",
            "fork_created",
            self.DESTINATION,
            router_input=ROUTER_INPUT,
            reservation_lease=reservation["reservation_lease"],
        )
        replay = confirm_stateful_event(
            "transfer-stateful",
            "fork_created",
            self.DESTINATION,
            router_input=ROUTER_INPUT,
        )
        resumed = create_stateful_receipt("transfer-stateful", self.DIGEST, ROUTER_INPUT)
        self.assertEqual((planned["state"], forked["state"]), ("planned", "fork_created"))
        self.assertEqual(replay, forked)
        self.assertEqual(resumed, forked)
        with self.assertRaisesRegex(ValueError, "event_already_confirmed"):
            reserve_stateful_event("transfer-stateful", "fork_created", router_input=ROUTER_INPUT)
        with self.assertRaisesRegex(ValueError, "transfer_id_already_bound"):
            create_stateful_receipt("transfer-stateful", "b" * 64, ROUTER_INPUT)

    def test_cli_requires_and_accepts_the_winner_reservation_lease(self) -> None:
        router_input_path = Path(self.temporary.name) / "router-input.json"
        router_input_path.write_text(json.dumps(ROUTER_INPUT), encoding="utf-8")
        environment = dict(os.environ)
        command = [
            sys.executable,
            str(SCRIPTS / "transfer_state.py"),
            "--router-input",
            str(router_input_path),
            "--transfer-id",
            "transfer-cli-lease",
        ]
        created = subprocess.run(
            [*command, "--new", "--prompt-sha256", self.DIGEST],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(json.loads(created.stdout)["state"], "planned")
        duplicate_source = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "transfer_state.py"),
                "--router-input",
                str(router_input_path),
                "--transfer-id",
                "transfer-cli-duplicate-source",
                "--new",
                "--prompt-sha256",
                self.DIGEST,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertNotEqual(duplicate_source.returncode, 0)
        self.assertIn("source_task_already_bound", duplicate_source.stderr)
        reserved = subprocess.run(
            [*command, "--reserve-event", "fork_created"],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        reservation = json.loads(reserved.stdout)
        denied = subprocess.run(
            [*command, "--event", "fork_created", "--destination-thread-id", self.DESTINATION],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("reservation_lease_required", denied.stderr)
        confirmed = subprocess.run(
            [
                *command,
                "--event",
                "fork_created",
                "--destination-thread-id",
                self.DESTINATION,
                "--reservation-lease",
                reservation["reservation_lease"],
            ],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(json.loads(confirmed.stdout)["state"], "fork_created")

    def test_cli_wrong_source_cannot_resume(self) -> None:
        router_input_path = Path(self.temporary.name) / "source-router-input.json"
        router_input_path.write_text(json.dumps(ROUTER_INPUT), encoding="utf-8")
        command = [
            sys.executable,
            str(SCRIPTS / "transfer_state.py"),
            "--router-input",
            str(router_input_path),
            "--transfer-id",
            "transfer-cli-source-bound",
        ]
        source_a = dict(os.environ, CODEX_THREAD_ID="cli-source-a")
        source_b = dict(os.environ, CODEX_THREAD_ID="cli-source-b")
        subprocess.run(
            [*command, "--new", "--prompt-sha256", self.DIGEST],
            check=True,
            capture_output=True,
            text=True,
            env=source_a,
        )
        subprocess.run(
            [*command, "--reserve-event", "fork_created"],
            check=True,
            capture_output=True,
            text=True,
            env=source_a,
        )

        wrong_source = subprocess.run(
            [*command, "--reserve-event", "fork_created"],
            check=False,
            capture_output=True,
            text=True,
            env=source_b,
        )
        self.assertNotEqual(wrong_source.returncode, 0)
        self.assertIn("state_file_missing", wrong_source.stderr)

    def test_prompt_delivery_requires_exact_destination_setting(self) -> None:
        receipt = self.advance(self.start("transfer-setting"), "fork_created")
        reserve_args, _ = self.arguments(receipt, "prompt_delivery_confirmed")
        winner = reserve_stateful_event("transfer-setting", "prompt_delivery_confirmed", **reserve_args)
        result = confirm_stateful_event(
            "transfer-setting",
            "prompt_delivery_confirmed",
            self.DESTINATION,
            self.DIGEST,
            router_input=ROUTER_INPUT,
            reservation_lease=winner["reservation_lease"],
            observed_model="different-model",
            observed_thinking=receipt["recommended_thinking"],
        )
        self.assertEqual((result["state"], result["uncertainty_reason"]), ("uncertain", "destination_setting_mismatch"))
        self.assertTrue(result["pending_reservation"])

    def test_timeout_is_terminal_and_preserves_pending_for_reconciliation(self) -> None:
        receipt = self.advance(self.start("transfer-timeout"), "fork_created")
        reserve_args, _ = self.arguments(receipt, "prompt_delivery_confirmed")
        reserve_stateful_event("transfer-timeout", "prompt_delivery_confirmed", **reserve_args)
        uncertain = confirm_stateful_event("transfer-timeout", "timeout", router_input=ROUTER_INPUT)
        repeated = confirm_stateful_event("transfer-timeout", "timeout", router_input=ROUTER_INPUT)
        self.assertEqual(uncertain, repeated)
        self.assertEqual(uncertain["state"], "uncertain")
        self.assertFalse(uncertain["archive_authorized"])
        self.assertEqual(uncertain["pending_reservation"]["event"], "prompt_delivery_confirmed")
        retry = reserve_stateful_event("transfer-timeout", "prompt_delivery_confirmed", **reserve_args)
        self.assertFalse(retry["side_effect_authorized"])

    def test_stale_evidence_can_confirm_pending_but_cannot_authorize_a_new_side_effect(self) -> None:
        self.start("transfer-stale-reconcile")
        winner = reserve_stateful_event(
            "transfer-stale-reconcile",
            "fork_created",
            router_input=ROUTER_INPUT,
        )
        later = datetime.now(timezone.utc) + timedelta(minutes=20)
        with patch("route_task._utc_now", return_value=later):
            confirmed = confirm_stateful_event(
                "transfer-stale-reconcile",
                "fork_created",
                self.DESTINATION,
                router_input=ROUTER_INPUT,
                reservation_lease=winner["reservation_lease"],
            )
            self.assertEqual(confirmed["state"], "fork_created")
            resumed = create_stateful_receipt(
                "transfer-stale-reconcile",
                self.DIGEST,
                ROUTER_INPUT,
            )
            self.assertEqual(resumed, confirmed)
            with self.assertRaisesRegex(ValueError, "route_not_authorized"):
                reserve_stateful_event(
                    "transfer-stale-reconcile",
                    "prompt_delivery_confirmed",
                    self.DESTINATION,
                    self.DIGEST,
                    router_input=ROUTER_INPUT,
                    observed_model=confirmed["recommended_model"],
                    observed_thinking=confirmed["recommended_thinking"],
                )

    def test_malformed_receipt_and_direct_reducer_bypass_are_rejected(self) -> None:
        base = new_receipt("transfer-malformed", self.DIGEST, ROUTER_INPUT)
        for field, value in (
            ("state", []),
            ("source_disposition", {}),
            ("archive_authorized", 1),
            ("confirmed_events", [{}]),
            ("pending_reservation", {"event": "fork_created"}),
        ):
            with self.subTest(field=field):
                malformed = copy.deepcopy(base)
                malformed[field] = value
                with self.assertRaises(ValueError):
                    validate_receipt(malformed, ROUTER_INPUT)
        module = importlib.import_module("transfer_state")
        self.assertEqual(module.__all__, ())
        self.assertFalse(hasattr(module, "_RESERVATION_GUARD"))
        self.assertFalse(hasattr(module, "transition"))
        self.assertFalse(hasattr(module, "confirm_reserved_event"))
        for name in (
            "atomic_write_receipt",
            "expected_state_chain",
            "reservation_directory",
            "create_stateful_receipt",
            "reserve_stateful_event",
            "confirm_stateful_event",
        ):
            self.assertFalse(hasattr(module, name))

    def test_thirty_fault_cases_never_duplicate_or_archive_early_in_modeled_ledger(self) -> None:
        faults = (
            "before_side_effect",
            "after_side_effect_timeout",
            "wrong_destination",
            "conflicting_duplicate",
            "incomplete_result",
            "reconciliation",
        )
        case_count = 0
        for operation_index, operation in enumerate(CONFIRMED_STATES):
            for fault in faults:
                with self.subTest(operation=operation, fault=fault):
                    case_count += 1
                    transfer_id = f"fault-{operation_index}-{fault}"
                    receipt = self.start(transfer_id)
                    counts = {event: 0 for event in CONFIRMED_STATES}
                    for prior in CONFIRMED_STATES[:operation_index]:
                        receipt = self.advance(receipt, prior)
                        counts[prior] += 1
                    reserve_args, confirm_args = self.arguments(receipt, operation)
                    winner = reserve_stateful_event(transfer_id, operation, **reserve_args)
                    if fault == "before_side_effect":
                        receipt = confirm_stateful_event(transfer_id, "timeout", router_input=ROUTER_INPUT)
                    elif fault in {"after_side_effect_timeout", "incomplete_result", "reconciliation"}:
                        counts[operation] += 1
                        if fault == "reconciliation":
                            retry = reserve_stateful_event(transfer_id, operation, **reserve_args)
                            self.assertFalse(retry["side_effect_authorized"])
                        receipt = confirm_stateful_event(
                            transfer_id,
                            "incomplete_result" if fault == "incomplete_result" else "timeout",
                            router_input=ROUTER_INPUT,
                        )
                    elif fault == "wrong_destination":
                        counts[operation] += 1
                        wrong_args = dict(confirm_args)
                        wrong_args["destination_thread_id"] = "wrong-destination"
                        receipt = confirm_stateful_event(
                            transfer_id,
                            operation,
                            reservation_lease=winner["reservation_lease"],
                            **wrong_args,
                        )
                    else:
                        counts[operation] += 1
                        receipt = confirm_stateful_event(
                            transfer_id,
                            operation,
                            reservation_lease=winner["reservation_lease"],
                            **confirm_args,
                        )
                        conflicting = dict(confirm_args)
                        if operation in {"prompt_delivery_confirmed", "destination_readback_confirmed"}:
                            conflicting["prompt_sha256"] = "b" * 64
                        else:
                            conflicting["destination_thread_id"] = "wrong-destination"
                        with self.assertRaises(ValueError):
                            confirm_stateful_event(transfer_id, operation, **conflicting)
                    self.assertLessEqual(max(counts.values()), 1)
                    if counts["source_archive_confirmed"]:
                        self.assertEqual(operation, "source_archive_confirmed")
                    validate_receipt(receipt, ROUTER_INPUT)
                    if receipt["archive_authorized"]:
                        self.assertEqual(receipt["state"], "navigation_confirmed")
        self.assertEqual(case_count, 30)

    def test_1260_synthetic_receipt_invariants(self) -> None:
        self.set_source("source-synthetic-invariants")
        planned = new_receipt("synthetic-invariants", self.DIGEST, ROUTER_INPUT)
        receipts = {"planned": planned}
        current = self.start("synthetic-state-bases", source_id="source-synthetic-invariants")
        for confirmed_event in CONFIRMED_STATES:
            current = self.advance(current, confirmed_event)
            receipts[current["state"]] = current
        receipts["uncertain"] = mark_uncertain(planned, "timeout")
        cases = 0
        accepted = 0
        states = ("planned", "fork_created", "prompt_delivery_confirmed", "destination_readback_confirmed", "navigation_confirmed", "source_archive_confirmed", "uncertain")
        events = (*CONFIRMED_STATES, *sorted(("timeout", "ambiguous_result", "delivery_unknown", "incomplete_result", "thread_id_mismatch", "prompt_digest_mismatch")), "invalid")
        destinations = (None, self.DESTINATION, "wrong-destination")
        digests = (None, self.DIGEST, "b" * 64, "", "c" * 64)
        for state in states:
            for event in events:
                for destination in destinations:
                    for digest in digests:
                        cases += 1
                        candidate = copy.deepcopy(receipts[state])
                        candidate["destination_thread_id"] = destination
                        candidate["prompt_sha256"] = digest
                        candidate["pending_reservation"] = {
                            "event": event,
                            "reservation_sha256": "d" * 64,
                            "lease_sha256": "e" * 64,
                            "prior_state_chain_sha256": confirmed_state_chain(candidate),
                        }
                        candidate["state_chain_sha256"] = expected_state_chain(candidate)
                        try:
                            validate_receipt(candidate, ROUTER_INPUT)
                        except ValueError:
                            continue
                        accepted += 1
                        next_index = len(candidate["confirmed_events"])
                        self.assertLess(next_index, len(CONFIRMED_STATES))
                        self.assertEqual(candidate["pending_reservation"]["event"], CONFIRMED_STATES[next_index])
                        self.assertEqual(candidate["prompt_sha256"], self.DIGEST)
                        self.assertEqual(bool(candidate["confirmed_events"]), destination is not None)
                        self.assertEqual(candidate["archive_authorized"], state == "navigation_confirmed")
        self.assertEqual(cases, 1260)
        self.assertEqual(accepted, 10)


if __name__ == "__main__":
    unittest.main()
