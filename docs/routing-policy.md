# Routing policy

[Simplified Chinese](i18n/zh-CN/routing-policy.md)

English is the authoritative source for this document.

## Minimum sufficient setting

The router recommends the lowest host-declared setting that its policy considers sufficient for the task profile. It does not assume that a stronger setting is always better.

## Model roles

- `deep`: ambiguous, high-risk, architecture, research, or final-decision work;
- `balanced`: ordinary implementation and analysis with moderate scope;
- `throughput`: clear, repetitive, low-risk, objectively verifiable work.

Concrete model identifiers come only from the live host role mapping.

## Reasoning effort

Reasoning effort is separate from model role. Clear local work may use a lower effort; multi-stage, high-risk, or weakly verifiable work moves upward. Unsupported effort values are never invented.

## Topology

`parallel` requires all of the following:

- several meaningful independent workstreams;
- low enough coupling;
- independent verification;
- acceptable write-conflict risk;
- explicit delegation authorization;
- independently observed parallelism evidence.

Permission alone is not evidence that parallelism exists.

## Valid decision tuples

The public contract accepts only:

```text
stay + none + none + keep
stay + efficiency + none + keep
reroute + quality + fork + archive_after_continuation_ready
reroute + parallelism + fork + archive_after_continuation_ready
```

For a new route or reservation, `unknown|stale|uncertain` evidence always reduces to `stay + none + none + keep`. An already durable `pending_reservation` follows the narrow TTL completion rule below. An `efficiency` benefit never automatically transfers because starting a new task only to save quota or latency can consume more time and tokens than it saves.

## Capability gate

A `reroute` output is only a candidate. The Codex Desktop orchestration layer must immediately verify:

- the current surface is Codex Desktop;
- all required task tools exist and their schemas are compatible;
- current-setting evidence is `verified` and current, preferring host injection and using the bounded local fallback only when host evidence is absent;
- model-catalog evidence is `verified` and current;
- the recommended `model` and `thinking` are supported;
- route evidence still matches the execution-time observations.
- `host_capabilities.source_task_context=true` is present in the routed host evidence, and a valid live current-source `CODEX_THREAD_ID` independently exists at transfer time.

If any check fails, no native task side effect is allowed and the recommendation remains advisory.

## Receipt-bound authorization

Receipt creation and every resumed transition must reuse the same canonical bounded router input. The reducer reruns the deterministic router and recomputes authorization before it accepts the next event; carrying forward a caller-supplied authorization string or receipt without that input is insufficient.

`authorization_binding` binds all of these fields:

- `source_binding_sha256`;
- `transfer_id`;
- `prompt_sha256`;
- `router_input_sha256`;
- `route_authorization`;
- `recommended_model`;
- `recommended_thinking`.

At `prompt_delivery_confirmed`, the adapter must provide the actual `model` and `thinking` values passed to the destination. Confirmation succeeds only when they exactly match `recommended_model` and `recommended_thinking`. Missing or mismatched values produce `uncertain` with a destination-setting mismatch.

`state_chain_sha256` binds `authorization_binding` to the ordered confirmation events, their destination, the prompt digest where required, the delivered setting at prompt delivery, and any terminal uncertainty reason. Reordered, omitted, backtracked, or inconsistent confirmation state is rejected.

The reducer derives `source_binding_sha256` locally from the current source task's valid `CODEX_THREAD_ID`. It never persists or outputs the raw source identifier. The hash is included in the per-source lock key, canonical receipt, `authorization_binding`, each reservation marker, and every transition validation. The same source cannot start a second transfer under another `transfer_id`; a different source cannot resume, confirm, or archive the first transfer. Missing, invalid, or mismatched source context fails closed. The declared `host_capabilities.source_task_context=true` gate and this runtime evidence are both required; neither can replace the other.

These bindings are deterministic integrity checks, not digital signatures. They do not authenticate the adapter or defend against a malicious local writer that can replace both the receipt and the bounded router input; that actor is outside the threat boundary.

Before each fork, send, readback, navigation, or archive side effect, the adapter must call `transfer_state.py --reserve-event` with the current receipt and the same `--router-input`. Reservation creation uses atomic `O_EXCL` files under the durable default `$CODEX_HOME/state/auto-route-for-codex` root or an explicit `AUTO_ROUTE_STATE_HOME`. The winning reserve durably records `pending_reservation` in the canonical receipt and returns both `side_effect_authorized=true` and a raw winner-only `reservation_lease`. Only that caller may perform the host call, and its matching `--event` confirmation must pass the lease through `--reservation-lease`. A repeated reserve returns `reconcile_required` if either the marker exists or the receipt remains pending, even if the marker is missing. Marker, receipt, and newly created state-directory updates are fsync'd before authorization is returned. Reconcile the operation and do not retry it.

The raw lease is an ephemeral coordination nonce and bearer capability, not a credential. The winning private local CLI or equivalent tool execution emits it once, and the adapter returns it as the `--reservation-lease` process argument; a future compatible interface may use stdin. Keep it inside that operation. Never copy it into task prompts, final or other user-facing prose, package or repository content, external telemetry, Issue or support reports, or durable logs. This rule does not defend against a malicious same-user writer.

Stale evidence never authorizes a new reserve. A reservation already durably recorded as `pending_reservation` while its immutable binding was valid may still be confirmed with the matching lease, or marked `uncertain`, after the evidence TTL. This completion path cannot authorize another host side effect. Use only the `transfer_state.py` CLI for mutation; Python imports and direct state-file edits are unsupported internals.

## Ordered continuation

For one eligible candidate, perform exactly one sequence:

1. rerun the router from the same bounded input and create a receipt only if the verified fork decision still holds;
2. reserve `fork_created`; only the reservation winner may fork with the same-directory environment, then confirm through `--event fork_created`, its returned `--reservation-lease`, and the same bounded input;
3. reserve `prompt_delivery_confirmed` with the prompt digest and actual `model` and `thinking`; only the winner may send once, then confirm through `--event prompt_delivery_confirmed`, its returned `--reservation-lease`, the same `--router-input`, `--observed-model`, and `--observed-thinking`;
4. reserve `destination_readback_confirmed`; only the winner may read that exact destination, verify the cleaned-prompt digest, and confirm the event with its returned `--reservation-lease` and the same input;
5. reserve `navigation_confirmed`; only the winner may navigate to the same destination and confirm the event with its returned `--reservation-lease` and the same input;
6. after `archive_authorized=true`, validate the same live source binding again, then reserve `source_archive_confirmed`; only the winner may archive the source and confirm the event with its returned `--reservation-lease` and the same input.

Do not create an unrelated fresh task, use a handoff that moves the same task state, or fall back to a second destination.

Once the destination has started, the source must not execute the original request.

## Failure policy

A timeout, incomplete result, ambiguous result, wrong destination, or prompt mismatch enters `uncertain`:

- do not resend or refork;
- do not execute the task in the source;
- do not archive the source;
- when a destination identifier is known, reconcile only by reading that destination.

If the fork succeeds but the host response is lost before any destination identifier is returned, durable replay protection still blocks refork, source execution, and source archive, but the plugin cannot discover the unknown destination. Keep the source visible and use the host UI or support channel to locate or recover the destination. This prevents duplicate execution; it does not prove zero lost tasks.

Duplicate confirmed events are idempotent. State jumps, backtracking, and automatic retries are rejected. A pre-existing marker or canonical `pending_reservation` is evidence that an external action may already have started, not permission to repeat it. Missing a marker does not clear a pending receipt or restore authorization.
