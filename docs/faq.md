# Frequently asked questions

[Simplified Chinese](i18n/zh-CN/faq.md)

English is the authoritative source for this document.

## Does the plugin automatically switch my model?

No. It returns a recommendation. The public edition does not modify the current task or persistent defaults.

## Does it create a new task?

No. Public decisions always stay in the current task.

## Why is the public edition less capable than the local-enhanced edition?

Native task continuation depends on host-specific evidence and orchestration that cannot be safely generalized. The public edition keeps only portable, auditable recommendation logic.

## Does a higher reasoning effort always improve quality?

No. The router treats quality, latency, quota use, task risk, and verifiability as separate considerations.

## Can it support future models?

Yes, without hard-coding them into policy. The host supplies logical role mappings and supported identifiers. Unknown combinations remain unresolved.

## Can another AI agent use it?

Not directly. Another agent may implement the versioned JSON contracts, but that integration must define its own activation, capability evidence, and side-effect boundaries.

## Does the project send telemetry?

No runtime telemetry is implemented.

## Is this an official OpenAI project?

No. It is an unofficial community project.
