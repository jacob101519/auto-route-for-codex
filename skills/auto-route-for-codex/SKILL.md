---
name: auto-route-for-codex
description: Explicitly route a Codex task to a sufficient model, reasoning effort, and execution topology. When verified Codex Desktop capabilities and evidence show a material quality or parallelism mismatch, continue through a fork and archive the source only after the destination is confirmed ready; otherwise stay and recommend safely. Never invoke implicitly.
---

# Auto Route for Codex

Run only after the host selects `$auto-route-for-codex`. Do not activate from ordinary task text.

## Route with bounded input

1. Build only the enumerated task profile in `schemas/router-input.schema.json`. Do not include the task text, local paths, thread identifiers, credentials, logs, or session-file contents in router input.
2. Prefer a host-injected current-setting observation. If it is absent and both `CODEX_THREAD_ID` and a usable `CODEX_HOME` are available, run `scripts/read_current_setting.py` as the bounded fallback. Accept only its `current` and `current_provenance` fields. It must not expose task text, a filesystem path, or a thread identifier. If it returns `unknown`, keep the source task and recommend only. Never substitute a persisted model default for the current task setting.
3. Observe the live model catalog, Codex surface, and exact host tool schemas. The plugin does not provide thread APIs; the host must inject them.
4. Bind current-setting, catalog, and host observations to separate, fresh provenance records. Treat their hashes as integrity checks, not signatures.
5. Run `scripts/route_task.py` with the versioned input. Accept only output that validates against `schemas/router-output.schema.json`.
6. Preserve the exact canonical bounded router input for the transfer lifecycle. `transfer_state.py --new` and every later resume transition must receive that same input; the reducer reruns the router and recomputes authorization before admitting each transition.
7. Require routing-time host evidence to declare `host_capabilities.source_task_context=true`. Before any transfer-state command, independently require a valid current-source `CODEX_THREAD_ID`. `transfer_state.py` derives `source_binding_sha256` locally and must never persist or output the raw source identifier. The declared gate and runtime evidence are both required; missing or invalid source context must fail closed.
8. Treat `delegation_authorized` as permission only, never as evidence that useful parallel work exists. A parallel transfer requires an independent `parallelism_observed=true` observation as well as delegation authorization.

Before any new reservation, if an observation is `unknown`, `stale`, or `uncertain`, or a required capability is missing, keep the source task and return a recommendation only. An already durable `pending_reservation` follows the narrow TTL completion rule below.

## Apply a stay decision

For `stay`, do not create, fork, navigate, or archive a task. Continue the original request in the source task. An `efficiency` benefit is advisory and never authorizes transfer.

## Apply a fork decision

Proceed only when the decision is exactly:

```text
reroute + quality|parallelism + fork + archive_after_continuation_ready
```

Immediately before side effects, re-check that the live surface is Codex Desktop and that these callable tools are present with compatible schemas:

- `codex_app__fork_thread`
- `codex_app__send_message_to_thread`
- `codex_app__read_thread`
- `codex_app__navigate_to_codex_page`
- `codex_app__set_thread_archived`

If the re-check differs from the routed evidence, stop and keep the source task.

Use `scripts/transfer_state.py` and `schemas/transfer-receipt.schema.json` to enforce this sequence. Every host side effect requires an atomic reservation first. The durable default private state root is `$CODEX_HOME/state/auto-route-for-codex`; `AUTO_ROUTE_STATE_HOME` is an explicit owner-controlled override and test hook for transfer state only:

1. Hash the original request after removing only the skill invocation token. Keep the request outside router input.
2. Give `transfer_state.py --new` the same bounded router input while the source task's valid `CODEX_THREAD_ID` is present. It must rerun the deterministic router and create a `planned` receipt only for a fresh, verified `reroute + quality|parallelism + fork` result; never accept a caller-supplied authorization string.
3. Require the locally derived `source_binding_sha256` to be part of the per-source lock key, canonical receipt, `authorization_binding`, every reservation marker, and every transition validation. The raw source identifier must not appear in CLI output or persisted state.
4. Require `authorization_binding` to bind `source_binding_sha256`, `transfer_id`, `prompt_sha256`, `router_input_sha256`, `route_authorization`, `recommended_model`, and `recommended_thinking` before any host side effect.
5. Before `codex_app__fork_thread`, run `transfer_state.py --reserve-event fork_created` with the receipt and the same `--router-input`. Call the host only when the result has `side_effect_authorized=true`, retain the winner-only `reservation_lease`, and then confirm with `--event fork_created`, `--reservation-lease`, the returned destination identifier, and the same `--router-input`.
6. Before `codex_app__send_message_to_thread`, reserve `prompt_delivery_confirmed` for that destination and prompt digest, passing `--observed-model` and `--observed-thinking` equal to the actual overrides that will be sent. Call the host exactly once only when `side_effect_authorized=true`, retain that reservation's winner-only `reservation_lease`, then confirm with `--event prompt_delivery_confirmed`, `--reservation-lease`, and the same destination, digest, setting arguments, and `--router-input`.
7. Before `codex_app__read_thread`, reserve `destination_readback_confirmed` for the same destination and prompt digest. Read only when `side_effect_authorized=true`, retain the winner-only `reservation_lease`, verify the digest, then confirm with `--event destination_readback_confirmed`, `--reservation-lease`, and the same `--router-input`.
8. Before `codex_app__navigate_to_codex_page`, reserve `navigation_confirmed` for the same destination. Navigate only when `side_effect_authorized=true`, retain the winner-only `reservation_lease`, then confirm with `--event navigation_confirmed`, `--reservation-lease`, and the same `--router-input`.
9. While the receipt is `navigation_confirmed` and `archive_authorized=true`, reserve `source_archive_confirmed` for the same destination before calling `codex_app__set_thread_archived(archived=true)`. Archive only when `side_effect_authorized=true`; omit `threadId` so the source task is the archive target, retain the winner-only `reservation_lease`, then confirm with `--event source_archive_confirmed`, `--reservation-lease`, and the same `--router-input`. The reducer must validate the current source binding again before archive confirmation.
10. Require `state_chain_sha256` to bind the ordered confirmation chain. Stop work in the source task and do not execute the original request twice.

Reservations use `O_EXCL` creation and contain only hashes and bounded transfer metadata, never raw task text. A successful reserve durably records `pending_reservation` in the canonical receipt before returning the raw winner-only `reservation_lease`; the receipt stores only its hash. Confirmation must present that lease through `--reservation-lease`. If either the canonical receipt has `pending_reservation` or the reservation marker already exists, a repeated reserve returns `reconcile_required` with `side_effect_authorized=false`, even if the other artifact is missing: reconcile the known operation and never retry that side effect. The reducer fsyncs every reservation marker and canonical receipt, and fsyncs each parent directory after creating a state directory or replacing a receipt. Reservation markers and receipts stay in `$CODEX_HOME/state/auto-route-for-codex` or the explicit `AUTO_ROUTE_STATE_HOME`. Do not change `AUTO_ROUTE_STATE_HOME` during an active transfer.

The per-source lock admits at most one canonical transfer. If the same source calls `--new` with another `transfer_id`, fail with `source_task_already_bound`. A wrong source normally derives a different per-source namespace and receives `state_file_missing`; if an already loaded receipt conflicts with the live binding, fail with `source_binding_mismatch`. In either case, reject resume, confirmation, and archive. Never accept a missing, malformed, caller-supplied, or persisted raw source identifier as a substitute for live source context.

Treat `reservation_lease` as an ephemeral coordination nonce and bearer capability, not a credential. The private local CLI or equivalent tool execution emits it once to the winning operation, which passes it back through the `--reservation-lease` process argument; a future compatible interface may use stdin instead. Keep the value inside that private operation. Never copy it into a task prompt, final or other user-facing prose, the plugin package or repository, external telemetry, an Issue or support report, or a durable log. This handling reduces accidental disclosure but does not protect the lease from a malicious same-user writer.

Expired or stale evidence never authorizes a new reservation. When an immutable binding and its reservation were validly and durably recorded as `pending_reservation` before the evidence TTL expired, the matching lease may still confirm only that already-started operation or mark it `uncertain` after the TTL. It must never authorize another host side effect. Invoke `transfer_state.py` only through its CLI for every state mutation. Python imports of the reducer implementation and direct state-file mutation are unsupported internals.

The receipt hashes provide deterministic integrity, not a digital signature. They detect inconsistent inputs, settings, bindings, and event order when the adapter and reducer follow this contract; they do not authenticate an issuer or defend against a malicious local writer that can replace both the receipt and its inputs. Such a writer is outside this threat boundary.

On timeout, mismatched thread ID, mismatched prompt digest, or incomplete result, transition to `uncertain`. Do not resend, do not archive, and do not replay the original request in the source. When a destination identifier is known, reconcile only that destination before any later action. If the fork succeeded but the host response was lost before any destination identifier was returned, durable replay protection still blocks refork, source execution, and source archive, but the Skill cannot discover the unknown destination. Keep the source visible and use the host UI or support channel to locate or recover it. This does not prove zero lost tasks.

## Boundaries

- Do not change the native model picker, global configuration, sandbox, network policy, approvals, or credentials.
- Do not claim that a Skill supplies host APIs.
- Do not archive after a fresh-task creation path. Only a confirmed fork continuation can authorize source archival.
- Keep routing output free of task text, local paths, thread identifiers, tokens, and credentials.
- Require a live valid `CODEX_THREAD_ID` for transfer while keeping the raw value out of transfer output and persisted state.
- Require `host_capabilities.source_task_context=true` as a routing gate without treating it as a substitute for runtime source evidence.
- Do not describe `route_authorization`, `authorization_binding`, or `state_chain_sha256` as a signature, credential, or defense against a malicious local writer.
- Do not copy fallback session contents, local reservation markers or receipts, or a raw `reservation_lease` into a task prompt, final or other user-facing prose, package, repository, external telemetry, Issue or support report, or durable log.
