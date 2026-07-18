---
translation_of: docs/configuration.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# 配置

[English](../../../docs/configuration.md)

## 不写入持久配置

Auto Route for Codex 不修改 `config.toml`、sandbox setting（沙箱设置）、approval policy（审批政策）、network access（联网权限）、credential（凭据）或持久化 Model default（模型默认值）。每个任务都必须通过 `$auto-route-for-codex` 单独激活。

## Input contract（输入契约）

Router（路由器）接收一个 JSON object（JSON 对象），其中包括：

- `current`：当前 Model（模型）、effort（推理档位）、status（状态）和观测时间；
- `profile`：描述任务的有限枚举、计数和布尔值；
- `host_models`：host（宿主）当前声明的 Model ID（模型编号）；
- `host_thinking`：host（宿主）当前声明的 reasoning value（推理值）；
- `host_role_models`：host（宿主）提供的逻辑 Model role mapping（模型角色映射）；
- `catalog_provenance` 和 `host_provenance`：有时间边界的观测元数据。

用户消息、文件内容、path（路径）、任务编号和 credential（凭据）都不是合法的 profile field（任务画像字段）。

## Resolution（解析）

只有同时满足以下条件，recommendation（建议）才是 `resolved`：

- 选中的 Model（模型）存在于 `host_models`；
- 逻辑角色通过 `host_role_models` 映射到该 Model（模型）；
- 选中的 reasoning value（推理值）存在于 `host_thinking`；
- 必需的 provenance（来源信息）仍在有效期内且内部一致。

否则结果为 `unresolved`，`tool_overrides` 为 null，并继续保持 `stay`。

## Invocation policy（调用政策）

`allow_implicit_invocation` 为 false。仅在引用或转发文字中出现插件名称不会激活它。请在 Codex composer（Codex 输入区）选择 Plugin（插件），或在任务开头输入 `$auto-route-for-codex`。
