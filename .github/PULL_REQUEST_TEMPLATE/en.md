## Summary

Describe the user-visible change and the problem it solves.

## Public boundary

- [ ] The change remains explicit opt-in.
- [ ] The public edition remains recommendation-only.
- [ ] No task prose, local path, credential, session identifier, private catalog, or runtime state is included.
- [ ] English documentation is authoritative and affected Simplified Chinese translations are synchronized.

## Verification

- [ ] `python3 scripts/verify_public_repo.py`
- [ ] `python3 -m unittest discover -s skills/auto-route-for-codex/tests -v`
- [ ] `python3 skills/auto-route-for-codex/scripts/validate_contracts.py`
- [ ] `python3 scripts/build_release.py --output-dir dist`

List any additional evidence and known limitations.
