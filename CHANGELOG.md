# Changelog

All notable public changes are recorded here.

## [Unreleased]

### Security

- allow the exact public GitHub service address `support@github.com` in scanned text while continuing to reject it as a commit identity, preventing Dependabot signatures from weakening or blocking full-history privacy verification.

## [0.5.0-alpha.2] - 2026-07-20

### Security

- replaced the personal email in all maintainer-controlled public branch and tag history with the GitHub `noreply` identity;
- added full reachable-history scanning for private email, personal paths, credentials, current and historical filenames, commit/tag identities and messages, and strict UTF-8 historical blobs;
- pinned the complete CI dependency closure with SHA-256 hashes and disabled checkout credential persistence;
- added annotated-tag, clean-worktree, full-history, exact-HEAD, protected-`main` ancestry, exact-CI, and immutable-release provenance gates;
- added a least-privilege tag-triggered release workflow with deterministic rebuild checks, artifact attestations, and a separate administration-read-only immutable-setting preflight token;
- added Dependabot configuration and repository hygiene exclusions for generated or runtime state.

### Compatibility

- the runtime routing and task-continuation contract is unchanged from `0.5.0-alpha.1`.

## [0.5.0-alpha.1] - 2026-07-20

### Added

- capability-gated Codex Desktop task continuation for verified `quality` and `parallelism` reroutes;
- public transfer-receipt contract and deterministic transfer-state reducer;
- ordered `fork -> send -> readback -> navigate -> archive` lifecycle;
- host-capability, current-setting, catalog, and supported-setting gates;
- host-injected current-setting preference with a bounded `read_current_setting.py` fallback for the exact current session when `CODEX_THREAD_ID` and `CODEX_HOME` are available;
- privacy-preserving source-task binding for every transfer: routing requires `host_capabilities.source_task_context=true`, runtime requires a valid `CODEX_THREAD_ID`, `source_binding_sha256` is derived locally, and the raw source identifier is never persisted or output;
- privacy-bounded current-setting output containing only the current setting and provenance, with `unknown` recommendation-only failure behavior;
- atomic `O_EXCL` event reservations under the durable default `$CODEX_HOME/state/auto-route-for-codex` private root before every external transfer action, with an explicit `AUTO_ROUTE_STATE_HOME` override and test hook;
- winner-only `reservation_lease` output, mandatory `--reservation-lease` confirmation, and canonical `pending_reservation` persistence;
- an explicit lease-disclosure contract: the ephemeral coordination nonce/bearer capability appears once in private local CLI stdout or equivalent execution detail, is passed back through argv, and is forbidden from prompts, user-facing prose, repositories, telemetry, reports, and durable logs;
- evidence-TTL handling that forbids new reservations from stale evidence while allowing only an already durable pending operation to be confirmed or marked `uncertain` with its immutable binding and matching lease;
- a CLI-only supported transfer-state mutation boundary; Python imports and direct state-file changes are unsupported;
- `side_effect_authorized` and `reconcile_required` results that prevent automatic retry when either a marker exists or the canonical receipt remains pending, including missing-marker recovery;
- fsync of reservation markers, canonical receipts, and parent directories for newly created state directories and receipt replacement;
- recommendation-only fallback for unsupported surfaces or `unknown|stale|uncertain` evidence;
- state-machine, failure-boundary, duplicate-prevention, and premature-archive tests;
- cross-`transfer_id` source locking and wrong-source resume/archive rejection;
- localized README entry points for 12 languages, with English as the authoritative source and a complete Simplified Chinese documentation set.

### Changed

- the public contract now permits `reroute + quality|parallelism + fork + archive_after_continuation_ready` only after the full execution-time gate passes;
- each confirmed transfer event still requires the same bounded `--router-input` and its winner-only `--reservation-lease`; `prompt_delivery_confirmed` also requires the actual `--observed-model` and `--observed-thinking` values;
- `efficiency` remains `stay + efficiency + none + keep`;
- documentation now distinguishes the portable router, the host-specific Codex Desktop adapter, and recommendation-only fallback surfaces.

### Security boundary

- a router decision alone never authorizes native task side effects;
- an external transfer action is authorized only by a newly created reservation that durably records `pending_reservation` and returns `side_effect_authorized=true` plus a raw winner-only `reservation_lease`; an existing marker or pending receipt requires reconciliation rather than retry;
- source archive is allowed only after destination delivery, readback, and navigation are confirmed;
- archive-time validation must confirm the same source binding used by the per-source lock, receipt, authorization binding, and reservation marker;
- timeout or ambiguity enters `uncertain` with no resend, refork, source execution, or archive;
- if a fork succeeds but the host response is lost before a destination identifier is returned, durable replay protection prevents refork, source execution, and source archive, but the plugin cannot discover the unknown destination; host-UI or support-assisted recovery is required and zero lost tasks are not claimed;
- current-session fallback output excludes task text, filesystem paths, task identifiers, credentials, and session records;
- reservation markers and canonical receipts contain only hashes and bounded transfer metadata, never raw task text, remain in the selected private state root, and are excluded from the package and repository; raw reservation leases are not persisted in those artifacts;
- deterministic integrity hashes are not digital signatures, and a malicious local writer remains outside the public threat boundary;
- private catalogs, credentials, external telemetry, durable logs, and persistent recommendation or global-configuration writes remain excluded; the one-time private local CLI lease output is the documented coordination exception and is not a credential.

## [0.4.0-alpha.1] - 2026-07-18

### Added

- explicit `$auto-route-for-codex` activation;
- deterministic recommendation-only router;
- strict public input and output contracts;
- semantic negative tests;
- English and Simplified Chinese documentation;
- public repository, privacy, translation, and release verification;
- Apache-2.0 licensing and GitHub community files.

### Security boundary

- current-setting evidence was supplied by the host in the 0.4 contract;
- no automatic transfer, archive, model change, credential use, or global configuration write.
