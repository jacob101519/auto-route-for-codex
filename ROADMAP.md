# Roadmap

## Before beta

- validate installation and deterministic export from a clean public clone;
- run real Codex Desktop end-to-end checks across supported host versions;
- validate bounded current-session fallback behavior across supported session layouts without collecting task text or task identifiers;
- validate atomic reservation, winner-only lease, durable canonical pending state, fsync, and reconciliation behavior across process interruption, concurrent invocation, missing markers, the default `$CODEX_HOME/state/auto-route-for-codex` root, and explicit `AUTO_ROUTE_STATE_HOME` overrides on supported Desktop hosts;
- verify before-side-effect and after-side-effect timeout handling;
- demonstrate zero duplicate execution and premature archive in real host end-to-end tests, and pursue zero-lost-task proof for fork-success/response-loss recovery as a future host E2E goal; local reducer simulations do not establish it;
- publish stable machine-readable host-capability metadata;
- expand real-world routing evaluations without collecting private prompts;
- document recommendation-only behavior for additional Codex surfaces;
- publish signed or attestable release provenance when the hosting workflow supports it.

## Before stable

- freeze the public routing, capability, and transfer contracts;
- define deprecation and migration windows;
- demonstrate backward-compatible upgrades and safe rollback;
- complete an independent security review of the routing and archive boundary;
- document the supported Codex Desktop host-version matrix with dated evidence.

## Non-goals

- modifying the native Codex model picker or adding a native `Auto` option;
- changing persistent model defaults or global Codex configuration;
- hidden or implicit invocation;
- automatic transfer for `efficiency`;
- transferring or archiving on unsupported or unverified hosts;
- collecting user prompts for analytics;
- exporting local transfer reservations, receipts, or session-derived runtime evidence;
- persisting or publishing raw reservation leases beyond the one-time private local CLI/tool execution that coordinates a winning operation;
- supporting state mutation through Python imports or direct state-file edits instead of the `transfer_state.py` CLI;
- treating deterministic integrity hashes as signatures or protection from a malicious local writer;
- claiming universal model rankings or cross-platform Desktop task-tool support.
