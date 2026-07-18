---
translation_of: docs/faq.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# 常见问题

[English](../../../docs/faq.md)

## Plugin（插件）会自动切换我的 Model（模型）吗？

不会。它只返回 recommendation（建议），不修改当前任务或持久默认值。

## 它会创建新任务吗？

不会。公开版 decision（决策）始终留在当前任务。

## 为什么公开版比本机增强版功能少？

Native task continuation（原生任务继续）依赖宿主特有证据和 orchestration（编排），无法安全地推广到不同宿主。公开版只保留可移植、可审计的 recommendation logic（建议逻辑）。

## 更高 reasoning effort（推理强度）一定会提高质量吗？

不一定。Router（路由器）会分别考虑质量、延迟、额度消耗、任务风险和可验证性。

## 它能支持未来 Model（模型）吗？

可以，不需要把未来 Model ID（模型编号）写死在政策中。host（宿主）提供逻辑角色映射和受支持编号；未知组合保持 `unresolved`。

## 其他 AI agent（AI 智能体）能使用吗？

不能直接使用。其他 Agent（智能体）可以实现带版本的 JSON contract（JSON 契约），但必须自行定义激活方式、capability evidence（能力证据）和 side-effect boundary（副作用边界）。

## 项目会发送 telemetry（遥测）吗？

没有实现任何运行时 telemetry（遥测）。

## 这是 OpenAI 官方项目吗？

不是，这是 unofficial community project（非官方社区项目）。
