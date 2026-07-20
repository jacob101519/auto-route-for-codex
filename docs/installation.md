# Installation, upgrade, uninstall, and rollback

[Simplified Chinese](i18n/zh-CN/installation.md)

English is the authoritative source for this document.

## Install a pinned release

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

Open a new Codex task after installation so the host can refresh its plugin catalog. Select **Auto Route for Codex** or invoke `$auto-route-for-codex`.

## Verify discovery

```sh
codex plugin marketplace list
codex plugin list
```

The installed selector should be `auto-route-for-codex@jacob101519`. Discovery proves that the package is visible; it does not prove model availability, verified evidence, compatible Desktop task tools, or a successful continuation.

## Verify the source package

From a clean clone:

The pinned packages below are required only for repository verification and release checks. They are not plugin runtime dependencies.

```sh
python3 -m pip install --disable-pip-version-check PyYAML==6.0.3 jsonschema==4.26.0
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

These checks validate deterministic policy, schemas, the bounded current-setting reader, reservation-backed transfer states, privacy rules, translations, and release packaging. They do not replace a real Codex Desktop end-to-end check.

## Upgrade

```sh
codex plugin marketplace upgrade jacob101519
codex plugin remove auto-route-for-codex@jacob101519
codex plugin add auto-route-for-codex@jacob101519
```

Review release notes before changing a pinned ref. `v0.5.0-alpha.1` expands the public contract from recommendation-only behavior to capability-gated Codex Desktop continuation.

## Uninstall

```sh
codex plugin remove auto-route-for-codex@jacob101519
codex plugin marketplace remove jacob101519
```

Uninstalling removes the plugin selection surface. It does not restore a source task that the host already archived, delete a destination task, change persistent model defaults, or automatically erase reservation markers and canonical receipts from `$CODEX_HOME/state/auto-route-for-codex` or `AUTO_ROUTE_STATE_HOME`. Inspect and reconcile task state before uninstalling during an `uncertain` or pending transfer; do not remove replay-protection state to force a retry.

## Roll back

Remove the current marketplace entry, then add the repository again with a previous release tag through `--ref`. Reinstall the plugin and start a new task.

Rolling back to `v0.4.0-alpha.1` restores the earlier recommendation-only public behavior. It does not undo task state or remove local reservation markers or canonical receipts created by a newer version. Reconcile any `pending_reservation` before rollback; a missing marker does not authorize retry.

Use only the `transfer_state.py` CLI to confirm or mark an existing pending operation `uncertain`. Python imports of the implementation and direct state-file mutation are unsupported. Expired evidence does not authorize a new reserve, but a matching lease may complete only the operation already durably bound as `pending_reservation` before the evidence TTL expired.

## Install from a source checkout

For development only:

```sh
codex plugin marketplace add /absolute/path/to/auto-route-for-codex
codex plugin add auto-route-for-codex@jacob101519
```

Run all verification commands before trusting a local checkout. Do not use a dirty or unreviewed checkout for an archive-capable end-to-end test.
