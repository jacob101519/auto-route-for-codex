---
translation_of: docs/privacy-and-data-flow.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# 隐私与数据流

[English](../../../docs/privacy-and-data-flow.md)

## 数据流

公开版只在 memory（内存）中处理一个很小的结构化 task profile（任务画像）：

```text
由宿主或用户提供的任务特征
  -> 严格 JSON 验证
  -> 确定性建议
  -> 结构化输出
```

Router（路由器）没有 network client（联网客户端）、credential store（凭据存储）、task manager（任务管理器）、telemetry pipeline（遥测管道）或持久化 recommendation state（建议状态）。

## 允许的数据

- task kind（任务类型）、scope（范围）、risk（风险）和 priority（优先级）等有限枚举；
- architecture signals（架构信号）和 parallel workstreams（并行工作流）等非负计数；
- 表示已独立确认任务特征的布尔值；
- host（宿主）声明的 Model ID（模型编号）和 reasoning value（推理值）；
- 有范围的 provenance timestamp（来源时间戳）和 content hash（内容指纹）。

## 禁止的数据

- 原始用户 prompt（提示）或任务历史；
- repository path（仓库路径）或文件内容；
- Codex task ID（Codex 任务编号）；
- cookie（登录信息）、credential（凭据）、access key（访问密钥）或 authentication header（认证头）；
- local session file（本机任务记录）、runtime log（运行日志）或 browser profile（浏览器资料）；
- 私有 model catalog（模型目录）或本机 marketplace configuration（插件市场配置）。

未知字段会被拒绝，而不是静默忽略。

## 持久化与联网行为

Router（路由器）不写文件，也不访问网络。从 GitHub 安装会由 Codex 或 Git 下载仓库内容，但运行时 recommendation logic（建议逻辑）本身离线。

## Public export control（公开导出控制）

源码项目通过 allowlist-only export（仅允许清单导出）构建公开仓库。Exporter（导出器）会拒绝未知源文件、symlink（符号链接）、本机路径、类似 UUID 的任务编号、配置的私有指纹和常见 secret value（机密值）模式。扫描能降低误泄露概率，但不能替代人工 Release review（发行复核）。
