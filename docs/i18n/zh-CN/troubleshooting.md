---
translation_of: docs/troubleshooting.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# 故障排查

[English](../../../docs/troubleshooting.md)

## 看不到 Plugin（插件）

1. 运行 `codex plugin marketplace list`。
2. 运行 `codex plugin list`。
3. 确认安装标识是 `auto-route-for-codex@jacob101519`。
4. 新建 Codex task（Codex 任务），让 host（宿主）刷新 Plugin catalog（插件目录）。

## 调用没有反应

公开 Skill（技能）只允许 opt-in（主动选择）。请选择 **Auto Route for Codex**，或在任务开头输入 `$auto-route-for-codex`。引用或 delegated text（委派文字）中的字面 token（调用词）不会激活它。

## recommendation（建议）是 unresolved（未解析）

这是 fail-closed（证据不足即停止）的正常行为。请检查 `host_models`、`host_thinking` 和 `host_role_models` 是否包含一致且受支持的组合，并确认 provenance timestamp（来源时间戳）仍然有效。

## 为什么没有转移到新任务

这是预期行为。公开版从不转移或归档任务，只推荐一个可以由用户或宿主单独应用的设置。

## Repository verification（仓库验证）失败

```sh
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
```

先修复第一个 invariant（不变量）错误。Release（发行）时不得绕过翻译、隐私、manifest（清单）或 schema（字段契约）检查。

## 需要更多帮助

使用 GitHub Discussions（GitHub 讨论）咨询用法；使用对应 Issue template（问题模板）报告可复现故障；安全问题使用 GitHub private vulnerability reporting（GitHub 私密漏洞报告）。
