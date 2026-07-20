# Compatibility

[Simplified Chinese](i18n/zh-CN/compatibility.md)

English is the authoritative source for this document.

Compatibility is a point-in-time claim and must be rechecked against the current Codex host.

| Surface | Public alpha behavior | Requirements and notes |
|---|---|---|
| Codex Desktop with all required task tools | Capability-gated full continuation | Explicit invocation, `host_capabilities.source_task_context=true`, valid current-source `CODEX_THREAD_ID`, verified current setting and catalog, compatible tool schemas, supported recommended `model` and `thinking`, and safe writable durable transfer state |
| Codex Desktop without complete or verified capability evidence | Recommendation-only fallback | No fork, resend, navigation, or archive |
| Codex CLI | Recommendation-only | Marketplace and local verification may work; Desktop task tools are not assumed |
| Codex IDE surfaces | Recommendation-only unless independently integrated | Plugin discovery and host controls vary by version |
| Codex cloud tasks | Recommendation-only | User model controls and Desktop task relationships may be unavailable |
| OpenAI API or Agents SDK | Separate integration required | A caller may implement an equivalent state machine but cannot claim a native Desktop continuation relationship |
| Other AI agents | Not directly supported | The JSON contracts may be adapted only with their own activation, evidence, and side-effect policy |

## Full-continuation requirements

The complete Codex Desktop path requires all of the following at execution time:

- explicit selection of **Auto Route for Codex** or `$auto-route-for-codex`;
- `host_capabilities.source_task_context=true` in routed host evidence and a valid live current-source `CODEX_THREAD_ID`; both are required and neither substitutes for the other;
- compatible `fork_thread`, `send_message_to_thread`, `read_thread`, `navigate_to_codex_page`, and `set_thread_archived` capabilities;
- `verified` and current current-setting evidence, using host injection first or the bounded `CODEX_THREAD_ID`/`CODEX_HOME` fallback when host evidence is absent;
- `verified` and current model-catalog evidence;
- a recommended `model` and `thinking` value declared by the live host;
- a valid `quality` or `parallelism` reroute candidate;
- safe owner-controlled `$CODEX_HOME/state/auto-route-for-codex` storage, or an explicit `AUTO_ROUTE_STATE_HOME`, with atomic `O_EXCL`, winner-only reservation lease, durable `pending_reservation`, and file/directory fsync support;
- successful destination delivery, readback, and navigation before archive.

If any requirement is unavailable, stale, unknown, uncertain, or incompatible, it cannot authorize a new reservation; the source stays visible and the output is advisory. A reservation already durably recorded as `pending_reservation` while its immutable binding was valid may still be confirmed with its matching lease, or marked `uncertain`, after the evidence TTL. That narrow completion path cannot authorize another host side effect.

## Repository requirements

- Python 3.11 or newer for repository verification scripts;
- plugin marketplace support for the documented installation flow;
- a valid `CODEX_THREAD_ID` for every transfer; a safe `$CODEX_HOME/sessions` tree is additionally required only when the current-setting fallback is needed;
- an owner-controlled, non-symlink durable `$CODEX_HOME/state/auto-route-for-codex` root or explicit `AUTO_ROUTE_STATE_HOME` for reservation-backed continuation;
- the `transfer_state.py` CLI as the only supported state-mutation interface; Python imports and direct state-file mutation are unsupported;
- a clean public clone for release verification.

## Version policy

The current target public version is `0.5.0-alpha.1`. Alpha versions may make incompatible contract changes. Git tags, plugin manifest versions, release titles, and release asset names must match.

## What compatibility does not mean

Successful installation does not guarantee a particular model, thinking value, or native task tool on every account or host. A passing unit test validates deterministic policy and modeled state transitions; only a real host end-to-end run can validate actual Desktop side effects.
