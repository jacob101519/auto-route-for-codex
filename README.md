# Auto Route for Codex

**Language:** English | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Alpha community project. Not an official OpenAI product.

Auto Route for Codex is an explicit opt-in Codex plugin that recommends a sufficient model role, reasoning effort, and execution topology from a privacy-bounded task profile. On a supported Codex Desktop host, it can continue a quality- or parallelism-sensitive task in a fork only after the host capability and evidence gates pass. Every other environment safely falls back to a recommendation in the current task.

## Why this exists

Model choice and reasoning effort are separate decisions. A short but risky task may need a stronger model, while a long, repetitive, verifiable job may benefit from a faster one. This plugin makes those tradeoffs explicit without silently changing persistent settings.

The public contract follows six rules:

- activation is explicit through `$auto-route-for-codex`;
- only enumerated profile fields reach the deterministic router;
- current setting prefers host-injected evidence; when that is absent, the bounded `read_current_setting.py` fallback may emit only `current` and `current_provenance`, and any `unknown` result stays recommendation-only;
- task continuation requires Codex Desktop, all required task tools, verified current-setting and catalog evidence, and a host-supported recommended model and thinking value;
- routing requires `host_capabilities.source_task_context=true`, and every transfer independently requires a valid `CODEX_THREAD_ID`; `transfer_state.py` derives a local `source_binding_sha256` and never persists or outputs the raw source identifier;
- every `fork -> send -> readback -> navigate -> archive` side effect requires its own atomic reservation, and the source may be archived only after the confirmed sequence reaches one destination.

## Quick start

Prerequisites:

- a Codex surface that supports plugins and explicit skill invocation;
- the Codex CLI available on `PATH`;
- access to the public Git repository.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

Start a new Codex task, select **Auto Route for Codex**, or invoke:

```text
$auto-route-for-codex Review this task and use a sufficient Codex setting.
```

The plugin always produces a versioned decision. It prefers a host-injected current setting. If that observation is absent and `CODEX_THREAD_ID` plus a usable `CODEX_HOME` are available, `read_current_setting.py` may inspect only the matching local session and emit a bounded `current + current_provenance` result without task text, a path, or a thread identifier. Reader failure returns `unknown`. On a capable Codex Desktop host, a verified `quality` or `parallelism` mismatch can continue in a fork with the recommended `model` and `thinking`; an `efficiency` mismatch, unsupported surface, missing tool, unsupported setting, or `unknown|stale|uncertain` evidence remains `stay` and recommendation-only.

The plugin does not modify the native model picker, `config.toml`, persistent defaults, sandbox settings, approval policy, network access, or credentials.

## Capability-gated Desktop continuation

The full path is available only when all of these checks pass:

1. the current surface is Codex Desktop;
2. the host exposes compatible `fork_thread`, `send_message_to_thread`, `read_thread`, `navigate_to_codex_page`, and `set_thread_archived` capabilities;
3. current-setting evidence is `verified` and current, using host injection first or the bounded fallback only when needed, and model-catalog evidence is also `verified` and current;
4. the recommended `model` and `thinking` are supported by the live host;
5. routed host evidence declares `host_capabilities.source_task_context=true`, and a valid live `CODEX_THREAD_ID` independently identifies the current source task to the local transfer reducer; the reducer derives `source_binding_sha256`, rejects missing or invalid source context, and never persists or outputs the raw source identifier; both the declared gate and runtime evidence are required;
6. before each fork, send, readback, navigation, or archive call, `transfer_state.py --reserve-event` creates an atomic `O_EXCL` marker and durably records `pending_reservation` in the canonical receipt; only the winning caller receives `side_effect_authorized=true` and a raw `reservation_lease`;
7. each confirmation must return that lease through `--reservation-lease`; prompt delivery also confirms the actual model and thinking overrides, destination readback proves that the cleaned original prompt reached the exact fork, and navigation succeeds before archive is authorized.

The ordered lifecycle is:

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

A successful reservation is followed by the host side effect and then a confirmation through `--event`, `--reservation-lease`, and the same `--router-input`; `prompt_delivery_confirmed` additionally requires `--observed-model` and `--observed-thinking`. The canonical receipt durably stores a hashed `pending_reservation`. A repeated reserve returns `reconcile_required` and `side_effect_authorized=false` when either the marker exists or the receipt remains pending, so a missing marker cannot reauthorize the side effect. Reconcile the known operation and do not retry it. The durable default private root is `$CODEX_HOME/state/auto-route-for-codex`; `AUTO_ROUTE_STATE_HOME` is an explicit owner-controlled override and test hook. Reservation markers and receipts contain only hashes and bounded transfer metadata, never raw task text. Marker writes, receipt writes, and newly created state directories are fsync'd before authorization is returned.

`source_binding_sha256` is included in the per-source lock key, canonical receipt, `authorization_binding`, every reservation marker, and the validation performed before every transition, including archive confirmation. Therefore one source task cannot start another transfer under a different `transfer_id`, and a different source task cannot resume, confirm, or archive the first source's transfer. Missing, malformed, or mismatched source context fails closed. The raw `CODEX_THREAD_ID` is used only to derive the local hash and is never written to a receipt or marker or returned by the transfer CLI.

`reservation_lease` is an ephemeral coordination nonce and bearer capability, not a credential. It is emitted once to the winning operation in private local CLI stdout or equivalent tool-execution detail and is passed back through process arguments as `--reservation-lease`; a future compatible interface may use stdin instead. Keep it inside that private operation. Never copy it into a task prompt, final or other user-facing prose, the package or repository, external telemetry, an Issue or support report, or a durable log. This boundary reduces accidental disclosure but does not protect the lease from a malicious same-user writer.

Expired or otherwise stale evidence never authorizes a new reservation. If a reservation was already durably recorded as `pending_reservation` while its immutable binding was valid, the matching lease may still confirm that exact operation or mark it `uncertain` after the evidence TTL. This narrow completion rule cannot authorize another host side effect. The only supported mutation interface is the `transfer_state.py` CLI. Python imports of its implementation and direct mutation of state files are unsupported internals.

A timeout, mismatch, incomplete result, or ambiguous side effect enters `uncertain`. The plugin must not resend, refork, execute the original request in the source, or archive the source. When a destination identifier is known, it may only reconcile that destination. If the fork actually succeeded but the host response was lost before any destination identifier was returned, durable replay protection still blocks refork, source execution, and source archive, but the plugin cannot discover the unknown destination itself. Keep the source visible and use the host UI or support channel to locate or recover the destination. This prevents duplicate execution; it does not prove zero lost tasks. Receipt and reservation hashes provide deterministic integrity, not signatures; a malicious local writer that can replace local state is outside the threat boundary.

## Public safety boundary

Included:

- strict JSON input, output, and transfer-receipt schemas;
- deterministic routing, bounded current-setting fallback, and reservation-backed transfer-state logic;
- privacy-preserving source-task binding that prevents cross-source resume and multiple transfer IDs for one source;
- a capability-gated Codex Desktop continuation contract;
- route, contract, semantic-negative, state-machine, and failure-boundary tests;
- public repository, privacy, translation, and release verification;
- authoritative English documentation, a complete Simplified Chinese translation, and localized README entry points.

Intentionally excluded:

- unbounded session scanning, task-text extraction, or exporting session contents, reservation markers, canonical receipts, or raw reservation leases;
- private current-setting receipts, private catalogs, or local marketplace state;
- runtime logs, credentials, personal paths, real task identifiers, or private configuration;
- hidden invocation, automatic transfer for `efficiency`, automatic model-picker changes, or global Codex configuration writes;
- claims that Codex CLI, IDE, cloud, API, or other agents expose Codex Desktop task tools.

See [Privacy and data flow](docs/privacy-and-data-flow.md), [Routing policy](docs/routing-policy.md), and [Compatibility](docs/compatibility.md).

## Repository map

| Path | Purpose |
|---|---|
| `.codex-plugin/plugin.json` | Plugin manifest |
| `.agents/plugins/marketplace.json` | Marketplace entry |
| `skills/auto-route-for-codex/` | Skill, schemas, bounded current-setting reader, router, reservation-backed transfer reducer, and tests |
| `docs/` | Authoritative English documentation |
| `docs/i18n/zh-CN/` | Complete Simplified Chinese translations |
| `scripts/verify_public_repo.py` | Repository, translation, privacy, and link checks |
| `scripts/build_release.py` | Deterministic plugin ZIP and `SHA256SUMS` builder |

## Verify from a clean clone

```sh
python3 -m pip install --disable-pip-version-check PyYAML==6.0.3 jsonschema==4.26.0
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

Passing local checks validates the package contract and modeled state transitions. It does not prove real Codex Desktop side effects on every host version; real end-to-end behavior remains host-dependent. Consult [Compatibility](docs/compatibility.md).

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

`v0.5.0-alpha.1` is the first public alpha with capability-gated Codex Desktop task continuation. The API, host-capability contract, and package layout may change before a stable release. See [CHANGELOG.md](CHANGELOG.md) and [ROADMAP.md](ROADMAP.md).

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report security issues through GitHub private vulnerability reporting as described in [SECURITY.md](SECURITY.md); do not publish sensitive reports in a public issue.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
