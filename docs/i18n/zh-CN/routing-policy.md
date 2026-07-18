---
translation_of: docs/routing-policy.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# 路由政策

[English](../../../docs/routing-policy.md)

## Minimum sufficient setting（最低充分设置）

Router（路由器）会推荐政策认为足以完成当前 task profile（任务画像）的最低设置，而不是默认认为越强越好。

## Model role（模型角色）

- `deep`：需求模糊、高风险、架构、研究或最终决策任务；
- `balanced`：常规实现和中等范围分析；
- `throughput`：目标清楚、重复、低风险且容易客观验证的任务。

具体 Model ID（模型编号）只来自 `host_role_models`。

## Reasoning effort（推理强度）

Router（路由器）把 reasoning effort（推理强度）和 Model role（模型角色）分开判断。清楚的局部任务可以使用较低档；multi-stage（多阶段）、high-risk（高风险）或 verification weak（难验证）的任务会提高档位。它不会发明 host（宿主）没有声明支持的档位。

## Topology（执行方式）

`parallel` 必须同时满足：

- 至少存在几个有意义且相互独立的 workstream（工作流）；
- coupling（耦合）足够低；
- 可以独立验证；
- write-conflict risk（写冲突风险）可接受；
- 已明确授权 delegation（委派）；
- 存在 parallelism observed（已观测并行）证据。

有 permission（权限）并不能证明并行事实存在。

## 公开 decision invariant（决策不变量）

每个公开输出都包含：

```json
{
  "action": "stay",
  "transfer": "none",
  "source_disposition": "keep"
}
```

`benefit` 可以是 `none` 或 `efficiency`。公开版永远不会输出 `fork`、授予 archive authority（归档授权）或修改 Codex task（Codex 任务）。
