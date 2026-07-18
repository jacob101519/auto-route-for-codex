# Privacy and data flow

[Simplified Chinese](i18n/zh-CN/privacy-and-data-flow.md)

English is the authoritative source for this document.

## Data flow

The public edition processes a small structured profile in memory:

```text
task characteristics supplied by the host or user
  -> strict JSON validation
  -> deterministic recommendation
  -> structured output
```

The router has no network client, credential store, task manager, telemetry pipeline, or persistent recommendation state.

## Allowed data

- bounded enum values such as task kind, scope, risk, and priority;
- non-negative counts such as architecture signals and parallel workstreams;
- booleans representing independently established task properties;
- host-declared model identifiers and reasoning values;
- bounded provenance timestamps and content hashes.

## Disallowed data

- raw user prompts or task history;
- repository paths or file contents;
- Codex task identifiers;
- cookies, credentials, access keys, or authentication headers;
- local session files, runtime logs, or browser profiles;
- private model catalogs or local marketplace configuration.

Unknown input fields are rejected rather than ignored.

## Persistence and network behavior

The router does not write files or call the network. Installing from GitHub necessarily downloads repository content through Codex or Git, but runtime recommendation logic itself is offline.

## Public export controls

The source project builds this repository through an allowlist-only export. The exporter rejects unrecognized source files, symlinks, local paths, UUID-shaped task identifiers, configured private fingerprints, and common secret-value patterns. A successful scan reduces accidental disclosure risk but is not a substitute for human release review.
