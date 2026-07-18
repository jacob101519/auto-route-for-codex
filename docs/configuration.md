# Configuration

[Simplified Chinese](i18n/zh-CN/configuration.md)

English is the authoritative source for this document.

## No persistent configuration writes

Auto Route for Codex does not modify `config.toml`, sandbox settings, approval policy, network access, credentials, or a persistent model default. Activation is per task through `$auto-route-for-codex`.

## Input contract

The router accepts one JSON object with:

- `current`: current model, effort, status, and observation time;
- `profile`: bounded enums, counts, and booleans describing the task;
- `host_models`: model identifiers the host currently declares;
- `host_thinking`: reasoning values the host currently declares;
- `host_role_models`: the host-provided mapping for logical model roles;
- `catalog_provenance` and `host_provenance`: bounded observation metadata.

User messages, file contents, paths, task identifiers, and credentials are not valid profile fields.

## Resolution

A recommendation is `resolved` only when:

- the selected model is present in `host_models`;
- the logical role maps to that model in `host_role_models`;
- the selected reasoning value is present in `host_thinking`;
- required provenance is current and internally consistent.

Otherwise the recommendation is `unresolved`, `tool_overrides` is null, and the decision still remains `stay`.

## Invocation policy

`allow_implicit_invocation` is false. Mentioning the plugin name in delegated content does not activate it. Select the plugin in the Codex composer or type `$auto-route-for-codex` at the start of the task.
