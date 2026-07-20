## Summary

Describe the user-visible change and the problem it solves.

## Public boundary

- [ ] The change remains explicit opt-in.
- [ ] Unsupported hosts remain recommendation-only; task continuation still requires every capability and evidence gate.
- [ ] No task prose, credential, private catalog, local runtime receipt, reservation marker, or raw `reservation_lease` is committed or packaged.
- [ ] Transfer-state mutation uses the `transfer_state.py` CLI, not Python imports or direct state-file edits.
- [ ] The current-setting fallback emits only bounded setting evidence, and transfer reservations remain local and fail closed.
- [ ] English documentation is authoritative and affected Simplified Chinese translations are synchronized.

## Verification

- [ ] `python3 -B scripts/verify_public_repo.py`
- [ ] `python3 -B -m unittest discover -s skills/auto-route-for-codex/tests -v`
- [ ] `python3 -B skills/auto-route-for-codex/scripts/validate_contracts.py`
- [ ] `python3 -B scripts/build_release.py --output-dir dist`

List any additional evidence and known limitations.
