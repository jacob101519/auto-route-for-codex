---
translation_of: docs/compatibility.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# 兼容性

[English](../../../docs/compatibility.md)

Compatibility（兼容性）是时点结论，必须根据当前 Codex host（Codex 宿主）重新检查。

| surface（使用界面） | 公开 Alpha 状态 | 说明 |
|---|---|---|
| Codex Desktop（Codex 桌面端） | 支持 host plugin discovery（宿主插件发现） | 显式调用，只提供建议 |
| Codex CLI（Codex 命令行工具） | 支持 marketplace installation（插件市场安装）和本地验证 | host model catalog（宿主模型目录）可能不同 |
| Codex IDE surface（Codex 编辑器界面） | 尚未验证 | package discovery（封装发现）可能随宿主版本变化 |
| Codex cloud task（Codex 云任务） | 尚未验证 | 用户可能无法控制 Model（模型） |
| 其他 AI agent（AI 智能体） | 不直接支持 | 可以由独立 integration（集成）适配 JSON contract（JSON 契约） |

## Host requirement（宿主要求）

- 支持 Plugin marketplace（插件市场）；
- 支持显式 Skill selection（技能选择）或 `$auto-route-for-codex`；
- 需要 resolved recommendation（已解析建议）时，由宿主提供 Model（模型）和 reasoning（推理）声明；
- repository verification script（仓库验证脚本）需要 Python 3.11 或更高版本。

## Version policy（版本政策）

当前支持的公开版本是 `0.4.0-alpha.1`。Alpha（早期测试）版本可能包含不兼容契约变更。Git tag（Git 标签）、Plugin manifest version（插件清单版本）、Release title（发行标题）和 Release asset filename（发行制品名称）必须一致。

## 兼容性不代表什么

安装成功并不保证每个账号或宿主都存在某个特定 Model（模型）。Router（路由器）只会解析运行时明确提供的值；缺少证据时返回 `unresolved` 建议。
