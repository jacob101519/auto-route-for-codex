# Frequently asked questions

[Simplified Chinese](i18n/zh-CN/faq.md)

English is the authoritative source for this document.

## Does the plugin automatically switch my current model?

No. It does not change the current task's native model picker or persistent defaults. When a verified Codex Desktop reroute is eligible, it passes the recommended `model` and `thinking` to the destination fork.

## Does it create a new task?

On a compatible Codex Desktop host, a verified `quality` or `parallelism` mismatch can continue in a fork. This is a continuation relationship, not an unrelated fresh task. `efficiency` decisions and unsupported surfaces stay in the source task.

## When is the source task archived?

Only after one destination has been forked, the cleaned prompt was sent once with the confirmed destination setting, destination readback confirms that prompt, navigation succeeds, and archive-time validation confirms the same source binding. Each external action first needs its own atomic reservation with `side_effect_authorized=true` and a winner-only `reservation_lease`; its matching confirmation must pass that lease through `--reservation-lease`. Archive is never authorized from a router decision alone.

## Why is `CODEX_THREAD_ID` required for transfer?

It identifies the current source task to the local reducer without being stored or printed. `transfer_state.py` derives `source_binding_sha256` and uses that hash in the per-source lock, receipt, authorization binding, reservation markers, and every transition check. This prevents the same source from starting another transfer with a different `transfer_id` and prevents another source from resuming or archiving the transfer. Missing, invalid, or mismatched source context fails closed. Routing also requires `host_capabilities.source_task_context=true`; that declaration and the runtime `CODEX_THREAD_ID` evidence are both required. The current-setting fallback is a separate use: host-injected current-setting evidence may avoid reading `$CODEX_HOME/sessions`, but it does not remove the source-binding requirement for transfer.

## What happens when a tool call times out?

The transfer enters `uncertain`. Its marker and canonical receipt remain as durable replay protection under `$CODEX_HOME/state/auto-route-for-codex` or the explicit `AUTO_ROUTE_STATE_HOME`. The plugin must not resend, refork, run the request again in the source, or archive. When a destination identifier is known, it may only reconcile that destination. If the fork succeeded but the host response was lost before any destination identifier was returned, replay protection still prevents refork, source execution, and source archive, but the plugin cannot discover the unknown destination. Keep the source visible and use the host UI or support channel to locate or recover it. This does not prove zero lost tasks. A canonical `pending_reservation` continues to block reauthorization even if its marker is missing.

## Why can the public edition now match the local experience?

The portable routing core, bounded current-setting fallback, transfer schema, reservation-backed state reducer, and safety tests can be public. Host-injected current setting remains preferred; the fallback exposes only `current` and provenance, and failure stays recommendation-only. Hosts that satisfy the public capability gate get the full path; other hosts safely receive recommendations only.

## Does a higher reasoning effort always improve quality?

No. The router treats quality, latency, quota use, task risk, and verifiability as separate considerations.

## Can it support future models?

Yes, without hard-coding them into routing policy. The live host supplies logical role mappings and supported identifiers. Unknown combinations remain advisory.

## Can another AI agent use it?

Not directly. Another agent may implement the versioned JSON and state-machine contracts, but it must define and validate its own activation, capability evidence, task relationship, and side-effect boundaries.

## Does the project send telemetry?

No runtime telemetry is implemented. The bounded reader accesses only the exact local session under `$CODEX_HOME/sessions` needed for current-setting evidence. Replay protection writes local reservation markers and canonical receipts containing hashes and transfer metadata, never raw task text, under `$CODEX_HOME/state/auto-route-for-codex` or `AUTO_ROUTE_STATE_HOME`. Raw winner-only reservation leases are not persisted in those artifacts. None of this state is transmitted as telemetry or included in the public repository.

## Is `reservation_lease` a credential, and where may it appear?

No. It is an ephemeral coordination nonce and bearer capability. The winning private local CLI or equivalent tool execution emits it once and passes it back as the `--reservation-lease` process argument; a future interface may use stdin. Do not copy it into task prompts, final or other user-facing prose, the package or repository, external telemetry, an Issue or support report, or a durable log. This boundary does not protect it from a malicious same-user writer.

## What if evidence expires while a reservation is pending?

Stale evidence cannot authorize a new reservation. A reservation already durably recorded as `pending_reservation` while its immutable binding was valid may still be confirmed with the matching lease, or marked `uncertain`, after the evidence TTL. It cannot authorize another host side effect. Use only the `transfer_state.py` CLI for state mutation; Python imports and direct state-file edits are unsupported.

## Is this an official OpenAI project?

No. It is an unofficial community project.
