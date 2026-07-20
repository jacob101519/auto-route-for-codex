# Configuration

[Simplified Chinese](i18n/zh-CN/configuration.md)

English is the authoritative source for this document.

## No persistent configuration writes

Auto Route for Codex does not modify `config.toml`, the native model picker, sandbox settings, approval policy, network access, credentials, or a persistent model default. Activation is per task through explicit selection or `$auto-route-for-codex`.

This no-configuration-write boundary does not mean zero local runtime state. For replay safety, `transfer_state.py --reserve-event` creates owner-only atomic reservation markers and canonical receipts under the durable default `$CODEX_HOME/state/auto-route-for-codex` root. `AUTO_ROUTE_STATE_HOME` is an explicit owner-controlled override and test hook for transfer state only. A winning reserve records `pending_reservation`, returns a raw `reservation_lease`, and requires the matching confirmation to pass it through `--reservation-lease`; only its digest is stored. Markers, receipts, and newly created state directories are fsync'd. They contain hashes and bounded transfer metadata, not configuration or raw task text, and are not copied into the package or repository.

Every transfer-state command also requires a valid current-source `CODEX_THREAD_ID`. The reducer derives `source_binding_sha256` locally, uses it for the per-source lock and canonical state namespace, and never writes or outputs the raw source identifier. `CODEX_THREAD_ID` is therefore required for transfer even when host-injected current-setting evidence made the session fallback unnecessary. Missing, invalid, or mismatched source context fails closed.

`reservation_lease` is an ephemeral coordination nonce and bearer capability, not a credential. It appears once in private local CLI stdout or equivalent tool-execution detail for the winning operation and is passed back through the `--reservation-lease` process argument; stdin may be supported by a future compatible interface. Never copy it into a task prompt, final or other user-facing prose, package or repository, external telemetry, Issue or support report, or durable log. This handling does not protect it from a malicious same-user writer.

Expired or stale evidence cannot authorize a new reservation. A valid reservation already durably recorded as `pending_reservation` may still be confirmed with its immutable binding and matching lease, or marked `uncertain`, after the evidence TTL; that exception cannot authorize another host side effect. Use only the `transfer_state.py` CLI to mutate transfer state. Python imports of the implementation and direct state-file mutation are unsupported internals.

## Routing input

The deterministic router accepts bounded structured facts such as:

- `current`: current model, effort, status, and observation time;
- `profile`: enums, counts, and booleans describing the task;
- host-declared model identifiers and thinking values;
- host-provided logical model-role mappings;
- bounded catalog and host provenance;
- the routing-time host declaration `host_capabilities.source_task_context=true` when trustworthy current-source context is available;
- independently observed parallelism and explicit delegation authorization.

User messages, file contents, repository paths, task identifiers, credentials, and session history are not valid router profile fields.

The `current` value prefers a host-injected observation. If it is absent, `read_current_setting.py` may use `CODEX_THREAD_ID` and `$CODEX_HOME/sessions` to read only the matching local session under strict safety limits. Its result contributes only `current` and `current_provenance`; failure returns `unknown` and cannot authorize continuation. `AUTO_ROUTE_STATE_HOME` changes only the transfer-state root; it does not change where current-setting evidence is read.

## Recommendation resolution

A recommendation is resolved only when the selected model and thinking value are declared by the live host, the logical role maps consistently, and required evidence is current and internally consistent. Unsupported combinations are never invented.

An unresolved recommendation cannot authorize continuation. The result stays advisory and keeps the source task.

## Continuation gate

A resolved recommendation still does not authorize native side effects by itself. Immediately before execution, a trusted Codex Desktop orchestration layer must verify:

- the current surface and required task-tool schemas;
- the current model and thinking value;
- current model-catalog evidence;
- support for the recommended `model` and `thinking`;
- an eligible `quality` or `parallelism` decision;
- `host_capabilities.source_task_context=true` in the routed host evidence and a valid live current-source `CODEX_THREAD_ID` at transfer time;
- one exact cleaned prompt and one exact destination;
- a fresh atomic reservation, durable canonical `pending_reservation`, and winner-only `reservation_lease` for the exact next side effect.

The declared `host_capabilities.source_task_context=true` gate and the runtime source context are both required; neither can substitute for the other. If the execution-layer observations differ from the route candidate, continuation is disabled. A host side effect runs only when reservation output contains `side_effect_authorized=true`; confirmation must present the returned lease through `--reservation-lease`. `reconcile_required` must be reconciled and never retried, including when the marker is missing but the canonical receipt remains pending.

## Invocation policy

`allow_implicit_invocation` is false. Mentioning the plugin name in quoted, copied, or delegated content does not activate it. Select the plugin in the Codex composer or place `$auto-route-for-codex` at the start of the task.

Explicit activation authorizes only the routing decision and its required task delegation. It does not grant new file, network, publication, credential, payment, or other authority.
