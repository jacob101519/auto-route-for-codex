# Contributing

Thank you for improving Auto Route for Codex.

## Before opening a change

- Use an Issue or Discussion for substantial policy changes.
- Keep the public edition recommendation-only.
- Do not add local paths, task identifiers, credentials, logs, or private catalogs.
- Update the authoritative English document and its complete Simplified Chinese translation together.
- Add or update deterministic tests for routing changes.

## Development checks

```sh
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

## Pull requests

A pull request should explain the problem, the contract or behavior changed, privacy impact, compatibility impact, and verification performed. Keep unrelated changes separate.

## Routing-policy changes

Policy changes require:

- at least one positive fixture;
- at least one negative or boundary fixture;
- proof that public outputs still cannot transfer or archive;
- an update to `docs/routing-policy.md` and its translation.

## Licensing

By contributing, you agree that your contribution is licensed under Apache-2.0.
