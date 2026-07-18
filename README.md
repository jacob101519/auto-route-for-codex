# Auto Route for Codex

[English](README.md) | [Simplified Chinese](README.zh-CN.md)

> Alpha community project. Not an official OpenAI product.

Auto Route for Codex is an explicit opt-in Codex plugin that recommends a sufficient model role, reasoning effort, and execution topology from a privacy-bounded task profile. The public edition is deliberately recommendation-only: it never forks, creates, navigates, archives, or replays a task.

## Why this exists

Model choice and reasoning effort are separate decisions. A short but risky task may need a stronger model, while a long, repetitive, verifiable job may benefit from a faster one. This plugin makes those tradeoffs explicit without turning model selection into an invisible side effect.

The public contract follows four rules:

- activation is explicit through `$auto-route-for-codex`;
- only enumerated profile fields reach the deterministic router;
- a recommendation resolves only against model and thinking values supplied by the host;
- every public decision remains `stay + none|efficiency + none + keep`.

## Quick start

Prerequisites:

- a Codex surface that supports plugins and explicit skill invocation;
- the Codex CLI available on `PATH`;
- access to the public Git repository.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

Start a new Codex task, select **Auto Route for Codex**, or invoke:

```text
$auto-route-for-codex Review this task and recommend a sufficient Codex setting.
```

The plugin returns a versioned recommendation. It does not change the current task's model or settings.

## Public safety boundary

Included:

- strict JSON input and output schemas;
- deterministic routing logic;
- recommendation-only tests and semantic negative cases;
- public repository and release verification scripts;
- English and complete Simplified Chinese documentation.

Intentionally excluded:

- local session-file readers;
- private current-setting receipts or catalogs;
- task fork, navigation, archive, and replay orchestration;
- runtime logs, credentials, local paths, task identifiers, or private configuration;
- automatic model changes or global Codex configuration writes.

See [Privacy and data flow](docs/privacy-and-data-flow.md) and [Routing policy](docs/routing-policy.md).

## Repository map

| Path | Purpose |
|---|---|
| `.codex-plugin/plugin.json` | Plugin manifest |
| `.agents/plugins/marketplace.json` | Marketplace entry |
| `skills/auto-route-for-codex/` | Skill, schemas, router, and tests |
| `docs/` | Authoritative English documentation |
| `docs/i18n/zh-CN/` | Complete Simplified Chinese translations |
| `scripts/verify_public_repo.py` | Repository, translation, privacy, and link checks |
| `scripts/build_release.py` | Deterministic plugin ZIP and `SHA256SUMS` builder |

## Verify from a clean clone

```sh
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

Passing local checks validate the repository contract. They do not prove that every Codex host version exposes the same plugin or model surface; consult [Compatibility](docs/compatibility.md).

## Documentation

- [Architecture](docs/architecture.md)
- [Installation and rollback](docs/installation.md)
- [Configuration contract](docs/configuration.md)
- [Privacy and data flow](docs/privacy-and-data-flow.md)
- [Routing policy](docs/routing-policy.md)
- [Compatibility](docs/compatibility.md)
- [Troubleshooting](docs/troubleshooting.md)
- [FAQ](docs/faq.md)

## Project status

`v0.4.0-alpha.1` is the first public alpha. The API and package layout may change before a stable release. See [CHANGELOG.md](CHANGELOG.md) and [ROADMAP.md](ROADMAP.md).

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report security issues through GitHub private vulnerability reporting as described in [SECURITY.md](SECURITY.md); do not publish sensitive reports in a public issue.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
