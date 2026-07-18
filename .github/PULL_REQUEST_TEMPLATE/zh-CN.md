## Summary（摘要）

说明用户能感知的改动以及它解决的问题。

## Public boundary（公开边界）

- [ ] 改动仍然需要 explicit opt-in（显式选择）。
- [ ] 公开版仍然只提供 recommendation（建议）。
- [ ] 不包含任务正文、本机路径、credential（凭据）、任务标识、私有 catalog（目录）或 runtime state（运行状态）。
- [ ] English documentation（英文文档）仍是权威原文，受影响的 Simplified Chinese translation（简体中文翻译）已经同步。

## Verification（验证）

- [ ] `python3 scripts/verify_public_repo.py`
- [ ] `python3 -m unittest discover -s skills/auto-route-for-codex/tests -v`
- [ ] `python3 skills/auto-route-for-codex/scripts/validate_contracts.py`
- [ ] `python3 scripts/build_release.py --output-dir dist`

请列出其他 evidence（证据）和 known limitation（已知限制）。
