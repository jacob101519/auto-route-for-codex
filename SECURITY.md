# Security policy

## Supported versions

Only the latest tagged public alpha receives security fixes. Older alpha versions may be unsupported.

## Report a vulnerability

Use GitHub private vulnerability reporting for this repository. Do not open a public Issue containing exploit details, credentials, private prompts, personal paths, task identifiers, or task data.

Include:

- affected version and commit;
- Codex surface and observed host capabilities;
- impact and realistic threat model;
- minimal sanitized reproduction;
- last confirmed transfer state and whether the result was `uncertain`;
- whether the issue can cause duplicate delivery, lost tasks, wrong-destination transfer, premature archive, configuration write, disclosure, or recommendation spoofing;
- suggested mitigation, if known.

## Critical transfer invariants

- explicit invocation is required;
- a router output alone cannot authorize native task tools;
- host-injected current-setting evidence is preferred; the bounded session fallback is used only when the host observation is missing and both `CODEX_THREAD_ID` and `CODEX_HOME` are available;
- fallback failure returns `unknown` and forces recommendation-only behavior;
- only verified `quality|parallelism` reroutes on a compatible Codex Desktop host are eligible;
- routing requires `host_capabilities.source_task_context=true`, and every transfer independently requires a valid live current-source `CODEX_THREAD_ID`; neither substitutes for the other;
- the reducer derives `source_binding_sha256` locally and never persists or outputs the raw source identifier;
- `source_binding_sha256` must bind the per-source lock key, canonical receipt, `authorization_binding`, each reservation marker, and every transition check, including archive confirmation;
- one source cannot start another transfer under a different `transfer_id`, and a wrong source cannot resume, confirm, or archive the transfer;
- before each external `fork`, `send`, `readback`, `navigate`, or `archive`, `transfer_state.py --reserve-event` must create an atomic `O_EXCL` reservation under the durable default `$CODEX_HOME/state/auto-route-for-codex` root or an explicitly configured `AUTO_ROUTE_STATE_HOME`;
- the external action may run only when the reservation durably records canonical `pending_reservation` and returns `side_effect_authorized=true` plus a raw winner-only `reservation_lease`;
- an existing marker or canonical pending reservation requires reconciliation and forbids retrying that external action, even when the other artifact is missing;
- a successful action is confirmed with the matching `--event`, returned `--reservation-lease`, and same `--router-input`; `prompt_delivery_confirmed` additionally requires the actual `--observed-model` and `--observed-thinking` values;
- reservation markers, canonical receipts, and newly created state directories must be fsync'd before authorization is returned;
- `fork -> send -> readback -> navigate` must succeed for one exact destination before archive;
- `unknown|stale|uncertain` evidence and missing capabilities fail closed for every new authorization;
- stale evidence never authorizes a new reservation; an already durable `pending_reservation` may use its immutable binding and matching lease only to confirm that exact operation or mark it `uncertain` after the evidence TTL;
- timeout or ambiguity must not trigger resend, refork, source execution, or archive;
- if a fork succeeds but its host response is lost before a destination identifier is returned, replay protection prevents refork, source execution, and source archive but cannot discover the unknown destination; keep the source visible and use the host UI or support channel for recovery, and do not claim zero lost tasks;
- the destination must inherit only the user's existing task authority, never expanded credentials or permissions.

Current-setting output is limited to the bounded current setting and its provenance; task text, filesystem paths, `CODEX_THREAD_ID`, and session records are excluded. Missing, malformed, or mismatched source context fails closed. Reservation markers and canonical receipts contain only integrity hashes and bounded transfer metadata, including `source_binding_sha256` but never the raw source identifier or raw task text, remain under `$CODEX_HOME/state/auto-route-for-codex` or `AUTO_ROUTE_STATE_HOME`, and must not enter the package, repository, Issue attachments, or release artifacts. The raw `reservation_lease` is an ephemeral coordination nonce and bearer capability, not a credential. It is emitted once in private local CLI stdout or equivalent tool-execution detail for the winning operation and is returned through the `--reservation-lease` process argument; a future compatible interface may use stdin. It must not be copied into task prompts, final or other user-facing prose, package or repository content, external telemetry, Issue or support reports, or durable logs. This handling does not protect it from a malicious same-user writer. The read-only current-setting fallback separately uses `$CODEX_HOME/sessions`.

Only the `transfer_state.py` CLI is a supported state-mutation interface. Python imports of the reducer implementation and direct changes to reservation markers or canonical receipts are unsupported and invalidate security assumptions.

Receipt hashes and the state chain provide deterministic integrity, not a digital signature. They do not authenticate the adapter or defend against a malicious local writer that can replace both the receipt and its bound inputs; that actor is outside the public threat boundary.

A violation that can lose a task, duplicate execution, archive the source prematurely, or send content to the wrong destination should be reported privately.

## Response goals

Maintainers aim to acknowledge a complete report within seven days. Timelines are goals, not service-level guarantees.

## Scope

The public repository includes a bounded current-session setting fallback, a capability-gated Codex Desktop continuation contract, and recommendation-only fallbacks when evidence or capabilities are insufficient. Reports about unrelated host behavior or third-party forks should be sent to their respective maintainers unless the public contract caused the issue.
