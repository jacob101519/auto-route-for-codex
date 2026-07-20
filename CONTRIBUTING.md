# Contributing

Thank you for improving Auto Route for Codex.

## Before opening a change

- Use an Issue or Discussion for substantial policy or host-capability changes.
- Keep invocation explicit and capability-gated.
- Do not add personal paths, real task identifiers, credentials, prompts, logs, or private catalogs.
- Do not capture a raw `reservation_lease` in fixtures, task prompts, final or user-facing prose, repository content, telemetry, Issues, support reports, or durable logs. It is an ephemeral bearer capability emitted once in private local CLI stdout or equivalent execution detail, not a credential and not protected from a malicious same-user writer.
- Treat the `transfer_state.py` CLI as the only supported state-mutation interface. Do not build features around importing its Python internals or directly editing transfer-state files.
- Do not treat router output as native task-tool authorization.
- Update the authoritative English document and its complete Simplified Chinese translation together.
- Refresh the capability paragraph, language navigation, and translation metadata in every localized README when public behavior changes.
- Add or update deterministic tests for routing, capability fallback, transfer state, and failure boundaries.

## Development checks

```sh
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

## Pull requests

A pull request should explain the problem, contract or behavior changed, privacy impact, compatibility impact, and verification performed. Keep unrelated changes separate.

## Routing and continuation changes

Policy or orchestration changes require:

- at least one positive fixture;
- at least one negative or boundary fixture;
- proof that `unknown|stale|uncertain` evidence stays advisory for every new authorization;
- proof that stale evidence cannot authorize a new reservation while an already durable pending reservation can only be confirmed or marked `uncertain` with its immutable binding and matching lease after TTL;
- proof that `efficiency` does not automatically transfer;
- proof that missing or incompatible host capabilities prevent all native task side effects;
- proof that `host_capabilities.source_task_context=true` and a valid live current-source `CODEX_THREAD_ID` are both required, the raw source identifier is neither persisted nor output, and missing or invalid source context fails closed;
- proof that one source cannot create multiple transfers under different `transfer_id` values and a wrong source cannot resume, confirm, or archive another source's transfer;
- proof that archive remains impossible before destination delivery, readback, and navigation;
- duplicate-execution, lost-task, and premature-archive failure cases;
- synchronized updates to `docs/routing-policy.md`, related English documents, Simplified Chinese translations, and localized README capability sections.

Modeled state-machine tests do not prove real host behavior. A release that changes Desktop orchestration must record the available real end-to-end evidence and its limits.

## Licensing

By contributing, you agree that your contribution is licensed under Apache-2.0.
