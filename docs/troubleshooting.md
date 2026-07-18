# Troubleshooting

[Simplified Chinese](i18n/zh-CN/troubleshooting.md)

English is the authoritative source for this document.

## The plugin does not appear

1. Run `codex plugin marketplace list`.
2. Run `codex plugin list`.
3. Confirm the installed selector is `auto-route-for-codex@jacob101519`.
4. Start a new Codex task so the host refreshes its plugin catalog.

## Invocation is ignored

The public skill is opt-in. Select **Auto Route for Codex** or place `$auto-route-for-codex` at the start of the task. A literal token inside quoted or delegated text is not activation.

## The recommendation is unresolved

This is fail-closed behavior. Check that `host_models`, `host_thinking`, and `host_role_models` contain a consistent supported combination and that provenance timestamps are current.

## The task did not move to a new task

Expected behavior. The public edition never transfers or archives tasks. It only recommends a setting for a user or host to apply separately.

## Repository verification fails

Run:

```sh
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
```

Fix the first reported invariant. Do not bypass translation, privacy, manifest, or schema checks for a release.

## Need more help

Use GitHub Discussions for usage questions and an Issue template for reproducible defects. Security reports belong in GitHub private vulnerability reporting.
