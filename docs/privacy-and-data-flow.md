# Privacy and data flow

[Simplified Chinese](i18n/zh-CN/privacy-and-data-flow.md)

English is the authoritative source for this document.

## Bounded data paths

Current-setting evidence uses this priority:

1. a host-injected observation;
2. only when host evidence is absent, `read_current_setting.py` with `CODEX_THREAD_ID` and a usable `CODEX_HOME`;
3. `unknown` and recommendation-only when the bounded fallback cannot produce reliable evidence.

The fallback verifies the exact session identifier internally and applies ownership, permission, symlink, size, line-count, candidate-count, and time limits. Its output contains only `current` and `current_provenance`, or `status=unknown` with a bounded reason. It never outputs task text, a session path, or the thread identifier.

The deterministic routing path processes only a bounded structured profile:

```text
task characteristics supplied by the host or user
  -> strict JSON validation
  -> deterministic route candidate
  -> advisory decision or continuation gate
```

Raw task text never enters the deterministic router.

When a verified Codex Desktop continuation is authorized, a separate host orchestration path handles the cleaned original prompt:

```text
cleaned original prompt
  + current source task from CODEX_THREAD_ID
  -> local source_binding_sha256 derivation
  -> prompt SHA-256 binding
  -> atomic reservation before each external operation
  -> one destination fork
  -> one host message delivery
  -> destination readback and digest confirmation
  -> navigation
  -> optional source archive
```

The prompt is sent to the destination task because the destination must perform the user's original request. It is not written into the routing profile, telemetry, or a public project log.

## Allowed router data

- bounded enum values such as task kind, scope, risk, and priority;
- non-negative counts such as architecture signals and parallel workstreams;
- booleans representing independently established task properties;
- host-declared model identifiers and thinking values;
- bounded provenance timestamps and integrity hashes;
- host-capability presence and schema-compatibility results.

The current-setting provenance source is either `host_current_setting` or `local_session_turn_context`. The latter identifies the evidence method, not a disclosure of session content.

## Bounded transfer data

The transfer state may temporarily hold:

- `source_binding_sha256`, derived locally from the current source task's valid `CODEX_THREAD_ID` without persisting or outputting the raw identifier;
- `transfer_id`;
- `prompt_sha256` for the cleaned prompt and `router_input_sha256` for the exact bounded router input reused on every resumed transition;
- `route_authorization`, recomputed by rerunning the deterministic router from that same bounded input;
- `recommended_model` and `recommended_thinking` for the destination setting;
- `authorization_binding`, which binds `source_binding_sha256`, `transfer_id`, `prompt_sha256`, `router_input_sha256`, `route_authorization`, `recommended_model`, and `recommended_thinking`;
- one destination task identifier returned by the host;
- ordered confirmed events, an uncertainty reason, and `state_chain_sha256` binding their order and event-specific confirmation data;
- a canonical `pending_reservation` containing the event, reservation digest, lease digest, and prior chain digest until that event is confirmed;
- one local reservation marker per external event, containing only hashes and bounded transfer metadata such as `transfer_id`, event, destination binding, prompt digest when required, delivery setting when required, and the lease digest.

`transfer_state.py` places each transfer under a per-source lock and canonical namespace derived from `source_binding_sha256`. That hash is present in the receipt, `authorization_binding`, reservation markers, and validation of every transition. `--reserve-event` writes owner-only reservation markers with atomic `O_EXCL` creation and durably persists the corresponding `pending_reservation` in the canonical receipt. The durable default private root is `$CODEX_HOME/state/auto-route-for-codex`; `AUTO_ROUTE_STATE_HOME` is an explicit owner-controlled override and test hook. Only the reservation winner receives the raw `reservation_lease`; the marker and receipt store its digest instead. The matching confirmation must return the lease through `--reservation-lease`. Markers and receipts contain no raw task text or raw source identifier, remain local, and are not telemetry, repository content, or release-package content. File and newly created directory updates are fsync'd before authorization is returned.

The raw lease is an ephemeral coordination nonce and bearer capability, not a credential. It is emitted once in private local CLI stdout or equivalent tool-execution detail for the winning operation and is passed back through the `--reservation-lease` process argument; a future compatible transport may use stdin. It must remain within that private operation. Do not copy it into task prompts, final or other user-facing prose, package or repository files, external telemetry, Issue or support reports, or durable logs. This handling reduces accidental disclosure but does not protect the lease from a malicious same-user writer.

At `prompt_delivery_confirmed`, the adapter must confirm the actual `model` and `thinking` values passed to the destination. The receipt does not accept the delivery confirmation when those values are absent or differ from the bound recommendation.

## Integrity and threat boundary

Every receipt creation and resumed transition requires the live current-source context, reuses the same bounded router input, and recomputes the route authorization. Routing additionally requires `host_capabilities.source_task_context=true`; the declared gate and runtime `CODEX_THREAD_ID` evidence are both required. `authorization_binding` detects a changed source, transfer, prompt digest, router input, authorization, or recommended destination setting. `state_chain_sha256` detects inconsistent confirmation order and binds destination, prompt-digest, delivery-setting, and uncertainty data where applicable.

One source task can own only one canonical transfer, so changing `transfer_id` cannot bypass replay protection. A different source cannot resume, confirm, or archive that transfer because its live `CODEX_THREAD_ID` derives a different binding. The same validation runs before archive confirmation. Missing, malformed, or mismatched source context fails closed.

Reservations close the stale-receipt replay gap for external actions: exactly one atomic creator receives `side_effect_authorized=true` and the raw winner-only `reservation_lease`. Every other caller receives `reconcile_required` and must inspect the known operation rather than retry it. The canonical receipt keeps `pending_reservation`, so deleting or losing the marker cannot make a repeated reserve eligible again.

Evidence TTL applies to new authorization: expired or stale evidence cannot authorize a new reservation. A reservation already durably stored as `pending_reservation` while its immutable binding was valid may still use the matching lease to confirm only that exact operation or mark it `uncertain` after the TTL. It cannot authorize another host side effect. `transfer_state.py` CLI is the only supported state-mutation interface; importing the Python implementation or directly changing state files is unsupported internals.

These SHA-256 values provide deterministic integrity, not a digital signature or issuer authentication. They assume the local adapter and reducer enforce the contract. A malicious local writer that can replace both a receipt and the corresponding router input can manufacture a self-consistent replacement and is outside the public threat boundary.

## Disallowed exported data

- real user prompts or task history in fixtures, receipts, or repository files;
- personal repository paths or proprietary file contents;
- real Codex task identifiers;
- cookies, credentials, access keys, or authentication headers;
- local session files, runtime logs, or browser profiles;
- local reservation markers, canonical receipts, or raw reservation leases from `$CODEX_HOME/state/auto-route-for-codex` or `AUTO_ROUTE_STATE_HOME`;
- private model catalogs or local marketplace configuration.

Unknown router fields are rejected rather than ignored.

## Network and host side effects

The deterministic router, fallback reader, and transfer reducer contain no telemetry client or credential store. The fallback reader performs a bounded read under `$CODEX_HOME/sessions`; the transfer reducer writes only local reservation markers and canonical receipts under `$CODEX_HOME/state/auto-route-for-codex` or the explicitly configured `AUTO_ROUTE_STATE_HOME`. Installing from GitHub downloads repository content through Codex or Git. During a full Desktop continuation, native Codex host tools perform the fork, message delivery, readback, navigation, and archive side effects; those effects remain governed by the host and the user's existing authority.

Explicit plugin activation does not grant new file, network, publication, credential, payment, or other authority to the destination task.

## Public export controls

The source project builds this repository through an allowlist-only export. The exporter rejects unrecognized source files, symlinks, personal paths, UUID-shaped task identifiers, local session data, reservation markers, configured private fingerprints, and common secret-value patterns. A successful scan reduces accidental disclosure risk but is not a substitute for human release review.
