# Installation, upgrade, uninstall, and rollback

[Simplified Chinese](i18n/zh-CN/installation.md)

English is the authoritative source for this document.

## Install a pinned release

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

Open a new Codex task after installation so the host can refresh its plugin catalog. Select **Auto Route for Codex** or invoke `$auto-route-for-codex`.

## Verify

```sh
codex plugin marketplace list
codex plugin list
```

The installed selector should be `auto-route-for-codex@jacob101519`. Installation proves that the package was discovered; it does not prove host model availability.

## Upgrade

```sh
codex plugin marketplace upgrade jacob101519
codex plugin remove auto-route-for-codex@jacob101519
codex plugin add auto-route-for-codex@jacob101519
```

Review release notes before changing a pinned ref.

## Uninstall

```sh
codex plugin remove auto-route-for-codex@jacob101519
codex plugin marketplace remove jacob101519
```

Uninstalling removes the plugin selection surface. It does not change your model defaults or archived tasks because this public edition never writes them.

## Roll back

Remove the current marketplace entry, then add the repository again with the previous release tag through `--ref`. Reinstall the plugin and start a new task.

## Install from a source checkout

For development only:

```sh
codex plugin marketplace add /absolute/path/to/auto-route-for-codex
codex plugin add auto-route-for-codex@jacob101519
```

Run the verification commands in the root README before trusting a local checkout.
