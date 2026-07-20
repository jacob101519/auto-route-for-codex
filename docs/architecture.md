# Architecture

[Simplified Chinese](i18n/zh-CN/architecture.md)

English is the authoritative source for this document.

## Design goal

The public edition turns a privacy-bounded task profile into a deterministic setting recommendation. On a supported Codex Desktop host, it may also continue a `quality`- or `parallelism`-sensitive task in a fork, but only after independent capability and evidence checks. For a new route or reservation, missing capability, unsupported settings, or `unknown|stale|uncertain` evidence reduces the result to an advisory `stay` decision. An already durable pending operation follows the separate TTL completion rule below.

The router separates four decisions:

1. `model_role`: `deep`, `balanced`, or `throughput`;
2. `thinking`: a reasoning value declared by the live host;
3. `topology`: `single`, `single_deep`, or `parallel`;
4. transfer: `none` or a capability-gated `fork`.

## Components

```text
Explicit invocation
  -> privacy-bounded task profile
  -> host-injected current setting
     -> or bounded local fallback when host evidence is absent
  -> current-setting, catalog, and host-capability validation
  -> deterministic route candidate
     -> advisory stay
     -> or Desktop continuation gate
          -> reserve event atomically and persist pending state
          -> perform one host side effect
          -> confirm with the winner-only reservation lease
          -> repeat for fork, send, readback, navigate, and archive
```

- `SKILL.md` defines explicit activation, the continuation gate, and the no-retry boundary.
- `read_current_setting.py` provides a bounded local session fallback only when host-injected current-setting evidence is absent; it emits only `current` and `current_provenance`, or `unknown`.
- `router-input.schema.json` rejects unknown fields and unbounded task text.
- `route_task.py` applies validation before routing policy.
- `router-output.schema.json` admits only valid `stay` and `reroute` tuples.
- `transfer-receipt.schema.json` binds one source task, one authorized transfer, one destination, the cleaned-prompt digest, the recommended destination setting, a durable `pending_reservation`, and every legal state/field combination.
- `transfer_state.py` requires a valid current-source `CODEX_THREAD_ID`, derives a privacy-preserving `source_binding_sha256`, and reruns the deterministic router from the same bounded input before creating a receipt and before every resumed transition. Before each host side effect, it creates one atomic `O_EXCL` reservation under the durable default `$CODEX_HOME/state/auto-route-for-codex` private root or an explicit `AUTO_ROUTE_STATE_HOME`, persists the corresponding `pending_reservation`, and returns a winner-only `reservation_lease`.
- `validate_contracts.py` checks positive, negative, and cross-field invariants.
- `verify_public_repo.py` checks packaging, translations, privacy markers, and links.

## Decision and execution boundary

A router output is a policy candidate, not permission to invoke native task tools. The orchestration layer must recheck the live surface, tool schemas, current setting, model catalog, supported model IDs, and supported thinking values immediately before a transfer. Current-setting evidence prefers a host-injected observation; only when it is absent may the bounded fallback use `CODEX_THREAD_ID` and `CODEX_HOME`. Routing also requires `host_capabilities.source_task_context=true`. Independently, every transfer requires a valid current-source `CODEX_THREAD_ID` for source binding, even when current-setting evidence came from host injection. The declared gate and runtime evidence are both required. A fallback `unknown` result or missing or invalid source context cannot authorize transfer.

Only a verified mismatch with `benefit=quality|parallelism` can use:

```text
reroute + quality|parallelism + fork + archive_after_continuation_ready
```

An `efficiency` mismatch never transfers automatically. It remains:

```text
stay + efficiency + none + keep
```

## Receipt integrity and resume contract

The canonical bounded router input is part of the transfer contract. Receipt creation and every resumed transition must receive the same input. Before accepting a transition, the reducer validates the existing receipt, reruns the deterministic router, recomputes the route authorization, and rejects a changed input digest, route, or recommended setting.

`authorization_binding` is the canonical SHA-256 digest of exactly:

- `source_binding_sha256`;
- `transfer_id`;
- `prompt_sha256`;
- `router_input_sha256`;
- `route_authorization`;
- `recommended_model`;
- `recommended_thinking`.

This prevents one receipt from being silently reused for a different source task, prompt, router input, route decision, transfer, or destination setting. At `prompt_delivery_confirmed`, the adapter must also supply the actual `model` and `thinking` values passed to the destination. They must equal `recommended_model` and `recommended_thinking`; missing or different values enter `uncertain`.

`state_chain_sha256` starts from `authorization_binding` and binds each confirmed event in order. The event binding includes the destination identifier, the prompt digest for delivery and readback confirmations, and the delivered model and thinking values for prompt delivery. An `uncertain` transition also binds its reason.

These hashes provide deterministic integrity, not a digital signature. They expose inconsistent inputs, authorization fields, destination settings, and event order when the adapter and reducer follow the contract. They do not authenticate an issuer or protect against a malicious local writer that can replace both the receipt and its inputs; that actor is outside the public threat boundary.

Each source task has one lock and one canonical receipt namespace derived from `source_binding_sha256`. The hash is included in the per-source lock key, receipt, `authorization_binding`, every reservation marker, and every transition validation. Each external operation then has a separate reservation keyed by that source binding, `transfer_id`, the prior `state_chain_sha256`, and event-specific bounded metadata. Atomic `O_EXCL` creation permits exactly one caller to receive `side_effect_authorized=true` plus the raw winner-only `reservation_lease`. Before returning, the reducer durably writes `pending_reservation` into the canonical receipt with the reservation digest, lease digest, event, and prior chain digest. A repeated reserve returns `reconcile_required` with `side_effect_authorized=false` if either the marker exists or the canonical receipt remains pending. A missing marker therefore cannot reauthorize an operation recorded as pending; the adapter must reconcile instead of retrying. The raw lease is required by the matching `--event` confirmation through `--reservation-lease`, but only its digest is stored. Markers and receipts are private runtime state, contain no raw task text or raw source identifier, and are not package or repository content. The reducer fsyncs marker and receipt files and fsyncs parent directories after creating state directories or replacing the canonical receipt. `AUTO_ROUTE_STATE_HOME` is an explicit owner-controlled override and test hook; do not switch roots during an active transfer.

One source task cannot create a second transfer under a different `transfer_id`. A source whose live `CODEX_THREAD_ID` derives a different hash cannot resume, confirm, or archive another source's transfer. The reducer validates this binding again before archive confirmation. Missing, malformed, or mismatched source context fails closed, while the raw source identifier is never persisted or returned by the transfer CLI.

The raw `reservation_lease` is an ephemeral coordination nonce and bearer capability, not a credential. The winning `transfer_state.py --reserve-event` process emits it once in private local CLI stdout or equivalent tool-execution detail; the adapter returns it as the `--reservation-lease` process argument, with stdin reserved as a possible future compatible transport. The adapter must keep it within that private operation and must not copy it into task prompts, final or other user-facing prose, package or repository files, external telemetry, Issue or support reports, or durable logs. This operational boundary reduces accidental disclosure but does not protect the value from a malicious same-user writer.

Evidence freshness gates new reservations, not completion of an already durable pending operation. Expired or stale evidence cannot authorize a new reserve. If an immutable binding and its reservation were validly recorded as `pending_reservation` before the evidence TTL expired, the matching lease may still confirm only that exact operation or mark it `uncertain` after the TTL; it cannot authorize another host side effect. `transfer_state.py` CLI is the only supported state-mutation interface. Python imports of the reducer implementation and direct state-file mutation are unsupported internals.

## Transfer lifecycle

The state sequence is linear:

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

Before every fork, send, readback, navigation, or archive side effect, the adapter must reserve the matching event while the same valid source context is active. It may call the host only when `side_effect_authorized=true`, retain the returned winner-only `reservation_lease`, then confirm the result through `--event`, `--reservation-lease`, and the same `--router-input`. Prompt delivery also supplies `--observed-model` and `--observed-thinking`. The source can be archived only after the exact destination readback proves the cleaned prompt, prompt delivery confirms the actual destination setting, navigation succeeds, and archive-time validation confirms the same source binding. Once the destination has started, the source must not execute the original request.

A timeout, ambiguous result, destination mismatch, prompt-digest mismatch, or incomplete result enters `uncertain`. In `uncertain`, the adapter must not resend, refork, run the source request, or archive. When `destination_thread_id` is known, reconciliation is limited to reading that destination. If the fork succeeds but the host response is lost before any destination identifier is returned, durable replay protection still blocks refork, source execution, and source archive, but the plugin cannot discover the unknown destination. Keep the source visible and use the host UI or support channel to locate or recover the destination. This prevents duplicate execution; it does not prove zero lost tasks.

## Trust boundaries

The router does not discover models or task tools. The live host supplies supported model and thinking values and exposes any Desktop task capabilities. Integrity hashes bind observations, transfer authorization, destination settings, and ordered state together; they do not authenticate an issuer, do not replace the live execution-layer recheck, and do not defend against a malicious local writer.

The bounded fallback reader accepts only the exact `CODEX_THREAD_ID`, applies ownership, permission, symlink, file-size, record-count, and time limits under `$CODEX_HOME/sessions`, and returns no task text, path, or thread identifier. Transfer state uses the separate durable `$CODEX_HOME/state/auto-route-for-codex` subtree or an explicit `AUTO_ROUTE_STATE_HOME`; markers and receipts contain hashes and bounded transfer metadata and are excluded from the package and repository. Task content still does not enter the deterministic router. During an authorized continuation, the host orchestration layer necessarily sends the cleaned original prompt to the destination fork.

## Surface boundary

The complete path is host-specific to a compatible Codex Desktop surface. Codex CLI, IDE, cloud, API, and other-agent integrations must be treated as recommendation-only unless they independently implement and validate an equivalent contract. No package installation alone proves that native task tools exist.
