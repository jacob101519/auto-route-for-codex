## Summary（摘要）

说明用户能感知的改动以及它解决的问题。

## Public boundary（公开边界）

- [ ] 改动仍然需要 explicit opt-in（显式选择）。
- [ ] 不受支持的 host（宿主）仍然只提供 recommendation（建议）；task continuation（任务继续）仍须通过全部能力与证据门槛。
- [ ] 不会提交或封装任务正文、credential（凭据）、私有 catalog（目录）、本机 runtime receipt（运行回执）、reservation marker（预留标记）或原始 `reservation_lease`（预留租约）。
- [ ] transfer-state mutation（转移状态修改）只使用 `transfer_state.py` CLI（命令行接口），不使用 Python import（Python 导入）或直接修改 state file（状态文件）。
- [ ] current-setting fallback（当前设置后备读取）只输出有边界的设置证据，transfer reservation（转移预留）保留在本机并 fail closed（证据不足即停止）。
- [ ] English documentation（英文文档）仍是权威原文，受影响的 Simplified Chinese translation（简体中文翻译）已经同步。

## Verification（验证）

- [ ] `python3 scripts/verify_public_repo.py`
- [ ] `python3 -m unittest discover -s skills/auto-route-for-codex/tests -v`
- [ ] `python3 skills/auto-route-for-codex/scripts/validate_contracts.py`
- [ ] `python3 scripts/build_release.py --output-dir dist`

请列出其他 evidence（证据）和 known limitation（已知限制）。
