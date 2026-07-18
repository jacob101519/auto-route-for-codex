---
translation_of: docs/architecture.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# 架构

[English](../../../docs/architecture.md)

## 设计目标

公开版把不包含任务正文的 task profile（任务画像）转换为 deterministic recommendation（确定性建议），同时不执行 Codex native side effect（Codex 原生副作用）。它分开处理三个决定：

1. `model_role`：`deep`、`balanced` 或 `throughput`；
2. `thinking`：host（宿主）明确支持的 reasoning effort（推理强度）；
3. `topology`：`single`、`single_deep` 或 `parallel`。

## 组成部分

```text
显式调用
  -> 有隐私边界的输入契约
  -> schema 与 provenance 验证
  -> deterministic route_task.py
  -> recommendation-only 输出契约
  -> 当前任务继续保留
```

- `SKILL.md` 定义显式激活和禁止转移的边界。
- `router-input.schema.json` 拒绝未知字段和没有边界的任务正文。
- `route_task.py` 先做硬验证，再应用政策规则。
- `router-output.schema.json` 把公开 decision（决策）限制为 `stay`。
- `validate_contracts.py` 验证正向示例和 semantic negative example（语义负向示例）。
- `verify_public_repo.py` 检查封装、翻译、隐私标记和链接。

## Trust boundary（信任边界）

Router（路由器）不会自行发现 Model（模型）。host（宿主）提供 `host_models`、`host_thinking` 和 `host_role_models`。provenance field（来源字段）只能证明 recommendation input（建议输入）在有限时间内一致；它不能认证发布者，也永远不能授权任务转移。

公开仓库没有 orchestration client（编排客户端）。即使 recommendation（建议）已经解析，仍只是一条建议；用户或宿主必须在 Plugin（插件）之外决定是否调整设置。

## 本机增强版与公开版

私有 local-enhanced edition（本机增强版）可以使用宿主特有证据和 task-continuation orchestration（任务继续编排）。这些能力无法在不同宿主之间安全、通用地建立权威证据，因此公开版刻意不包含它们。公开输出不得被其他版本当成 transfer authorization（转移授权）。
