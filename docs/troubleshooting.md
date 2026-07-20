# Troubleshooting

[Simplified Chinese](i18n/zh-CN/troubleshooting.md)

English is the authoritative source for this document.

## The plugin does not appear

1. Run `codex plugin marketplace list`.
2. Run `codex plugin list`.
3. Confirm the installed selector is `auto-route-for-codex@jacob101519`.
4. Start a new Codex task so the host refreshes its plugin catalog.

## Invocation is ignored

The skill is opt-in. Select **Auto Route for Codex** or place `$auto-route-for-codex` at the start of the task. A literal token inside quoted or delegated text is not activation.

## The recommendation is unresolved

This is fail-closed behavior. Check that the live host declares a consistent supported model, thinking value, and role mapping and that required current-setting and catalog evidence is current. Host-injected current setting has priority. If it is absent, the bounded fallback needs a valid `CODEX_THREAD_ID`, a safe `CODEX_HOME` session tree, and one exact readable session; any failure returns `unknown` without exposing task text, a path, or a thread identifier.

## The task stayed in the source

This is expected when any continuation requirement is missing. Common causes include:

- the surface is not Codex Desktop;
- one or more required task tools is absent or schema-incompatible;
- the route benefit is `none` or `efficiency`;
- current-setting or catalog evidence is `unknown`, `stale`, or `uncertain`;
- the recommended model or thinking value is unsupported;
- the execution-time recheck differs from the route candidate.
- `host_capabilities.source_task_context` is not `true`, or `CODEX_THREAD_ID` is missing, malformed, or does not match the source bound to the canonical transfer receipt.

The plugin should still provide an advisory recommendation when enough routing information exists.

`CODEX_THREAD_ID` has two distinct roles. The current-setting fallback uses it only when host-injected current-setting evidence is absent. Transfer source binding requires it for every transfer, and routing independently requires `host_capabilities.source_task_context=true`. The reducer hashes the runtime identifier locally as `source_binding_sha256` and never writes or prints the raw identifier. The declared gate and runtime evidence are both required.

## The transfer reports a source binding error

`source_thread_context_required` means the live `CODEX_THREAD_ID` is missing or invalid. `state_file_missing` commonly means the active source derived a different per-source namespace, so no canonical receipt exists there; this is the usual wrong-source result. `source_binding_mismatch` means an already loaded receipt conflicts with the live source binding and should be treated as moved, forged, or corrupted state. `source_task_already_bound` means this source already owns a transfer under another `transfer_id`. Do not change or fabricate `CODEX_THREAD_ID`, create another `transfer_id`, move or edit the receipt, or retry a side effect. Return to the original source task and reconcile its existing transfer. A wrong source cannot resume, confirm, or archive it.

## The reservation says reconcile required

`reconcile_required` with `side_effect_authorized=false` means an atomic marker exists or the canonical receipt still has `pending_reservation` for that exact event. The external operation may already have started. Do not delete the marker or receipt and do not repeat the fork, send, readback, navigation, or archive call. A missing marker does not clear the pending receipt or restore authorization. If a destination identifier is known, reconcile that destination and the last confirmed receipt state first. If no destination identifier was returned, do not refork; keep the source visible and follow the timeout recovery guidance below.

Reservation state uses the durable default `$CODEX_HOME/state/auto-route-for-codex` root. `AUTO_ROUTE_STATE_HOME` is an explicit owner-controlled override and test hook; keep the selected root unchanged through an active transfer and reconciliation. The current-setting fallback still reads only `$CODEX_HOME/sessions`. Successful reserve output contains a winner-only `reservation_lease`, and the matching `--event` confirmation must pass it through `--reservation-lease`; a missing or mismatched lease is not permission to retry. Marker, receipt, and newly created directory updates are fsync'd before authorization is returned.

That lease is an ephemeral coordination nonce and bearer capability, not a credential. It appears once in private local CLI stdout or equivalent tool-execution detail and is passed back as the `--reservation-lease` process argument; a future compatible interface may use stdin. Do not copy it into task prompts, final or other user-facing prose, package or repository content, external telemetry, Issue or support reports, or durable logs. A malicious same-user writer remains outside this protection boundary.

If evidence expires, do not reserve again. A reservation already durably stored as `pending_reservation` while its immutable binding was valid may still be confirmed with the matching lease, or marked `uncertain`, after the evidence TTL; it cannot authorize another side effect. Use the `transfer_state.py` CLI for all state mutation. Python imports and direct edits to marker or receipt files are unsupported and can invalidate reconciliation evidence.

## The destination started but the source is still visible

Do not manually invoke the plugin again and do not resend the original request. The transfer may be `uncertain`, or destination readback/navigation/archive may not have been confirmed. Reconcile the already known destination first. Keeping the source visible is safer than premature archive.

## The source was archived

Archive is expected only after destination delivery, readback, and navigation were confirmed. Continue in the destination task. If the destination does not contain the original request, treat this as a security-sensitive premature-archive defect and report it privately.

## A tool call timed out

Do not retry by creating another destination. A timeout after a possible side effect enters `uncertain`; the reservation remains replay protection. When a destination task identifier is known, reconcile only through that destination. If the fork succeeded but the host response was lost before any destination identifier was returned, replay protection still prevents refork, source execution, and source archive, but the plugin cannot discover the unknown destination. Keep the source visible and use the host UI or support channel to locate or recover it. This does not prove zero lost tasks.

## Repository verification fails

Run:

```sh
python3 -B scripts/verify_public_repo.py --require-git-history
python3 -B -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 -B skills/auto-route-for-codex/scripts/validate_contracts.py
```

Fix the first reported invariant. Do not bypass translation, privacy, manifest, schema, or transfer-state checks for a release.

## Need more help

Use GitHub Discussions for usage questions and an Issue template for reproducible defects. Include the version, Codex surface, capability-gate result, decision tuple, last confirmed transfer state, reservation status without local paths or task identifiers, and sanitized verification output. Security reports belong in GitHub private vulnerability reporting.
