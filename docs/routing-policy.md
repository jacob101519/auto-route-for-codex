# Routing policy

[Simplified Chinese](i18n/zh-CN/routing-policy.md)

English is the authoritative source for this document.

## Minimum sufficient setting

The router recommends the lowest declared setting that its policy considers sufficient for the task profile. It does not assume that a stronger setting is always better.

## Model roles

- `deep`: ambiguous, high-risk, architecture, research, or final-decision work;
- `balanced`: ordinary implementation and analysis with moderate scope;
- `throughput`: clear, repetitive, low-risk, objectively verifiable work.

Concrete model identifiers come only from `host_role_models`.

## Reasoning effort

The router treats reasoning effort as separate from model role. Clear local work may use a lower effort; multi-stage, high-risk, or weakly verifiable work moves upward. Unsupported effort values are never invented.

## Topology

`parallel` requires all of the following:

- at least several meaningful independent workstreams;
- low enough coupling;
- independent verification;
- acceptable write-conflict risk;
- explicit delegation authorization;
- observed parallelism evidence.

Permission alone is not evidence that parallelism exists.

## Public decision invariant

Every public output has:

```json
{
  "action": "stay",
  "transfer": "none",
  "source_disposition": "keep"
}
```

`benefit` may be `none` or `efficiency`. The public edition never emits `fork`, never grants archive authority, and never changes a Codex task.
