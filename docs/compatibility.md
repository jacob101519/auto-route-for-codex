# Compatibility

[Simplified Chinese](i18n/zh-CN/compatibility.md)

English is the authoritative source for this document.

Compatibility is a point-in-time claim and must be rechecked against the current Codex host.

| Surface | Public alpha status | Notes |
|---|---|---|
| Codex Desktop | Supported with host plugin discovery | Explicit invocation; recommendation only |
| Codex CLI | Supported for marketplace installation and local verification | Host model catalog may differ |
| Codex IDE surfaces | Not yet verified | Package discovery can vary by host version |
| Codex cloud tasks | Not verified | User model controls may be unavailable |
| Other AI agents | Not directly supported | The JSON contracts may be adapted by a separate integration |

## Host requirements

- plugin marketplace support;
- explicit skill selection or `$auto-route-for-codex`;
- host-supplied model and reasoning declarations when a resolved recommendation is desired;
- Python 3.11 or newer for repository verification scripts.

## Version policy

The current supported public version is `0.4.0-alpha.1`. Alpha versions may make incompatible contract changes. Git tags, plugin manifest versions, release titles, and release asset names must match.

## What compatibility does not mean

Successful installation does not guarantee that a specific model exists on every account or host. The router resolves only against values supplied at runtime and falls back to an unresolved advisory when evidence is missing.
