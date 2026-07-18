# Architecture

[Simplified Chinese](i18n/zh-CN/architecture.md)

English is the authoritative source for this document.

## Design goal

The public edition converts a privacy-bounded task profile into a deterministic recommendation without performing native Codex side effects. It separates three decisions:

1. `model_role`: `deep`, `balanced`, or `throughput`;
2. `thinking`: the host-supported reasoning effort;
3. `topology`: `single`, `single_deep`, or `parallel`.

## Components

```text
Explicit invocation
  -> privacy-bounded input contract
  -> schema and provenance validation
  -> deterministic route_task.py
  -> recommendation-only output contract
  -> current task stays active
```

- `SKILL.md` defines explicit activation and the no-transfer boundary.
- `router-input.schema.json` rejects unknown fields and unbounded task text.
- `route_task.py` applies hard validation before policy rules.
- `router-output.schema.json` restricts public decisions to `stay`.
- `validate_contracts.py` validates positive and semantic negative examples.
- `verify_public_repo.py` checks packaging, translations, privacy markers, and links.

## Trust boundaries

The router does not discover models. The host supplies `host_models`, `host_thinking`, and `host_role_models`. Provenance fields establish bounded consistency for recommendation input; they do not authenticate an issuer and never authorize task transfer.

The public repository contains no orchestration client. Even a resolved recommendation is advisory. A host or user must decide whether to change settings outside this plugin.

## Local-enhanced versus public edition

The private local-enhanced edition may use host-specific evidence and task-continuation orchestration. Those capabilities are intentionally absent here because they cannot be made portable or safely authoritative across hosts. Public output from this repository must never be treated as transfer authorization for another edition.
