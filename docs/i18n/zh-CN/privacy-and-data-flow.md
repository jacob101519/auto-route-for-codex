---
translation_of: docs/privacy-and-data-flow.md
source_revision: docs-v0.5.0-alpha.1
last_synced_version: 0.5.0-alpha.1
---

# 隐私与数据流

[English](../../../docs/privacy-and-data-flow.md)

## 有边界的 data path（数据路径）

Current-setting evidence（当前设置证据）采用以下优先级：

1. host-injected observation（宿主注入观测）；
2. 只有缺少宿主证据时，才使用带 `CODEX_THREAD_ID` 和可用 `CODEX_HOME` 的 `read_current_setting.py`；
3. bounded fallback（有限后备读取器）无法得到可靠证据时，返回 `unknown` 并保持 recommendation-only（仅建议）。

Fallback（后备读取器）会在内部验证精确 session identifier（任务记录编号），并限制 owner（所有者）、permission（权限）、symlink（符号链接）、size（大小）、line count（行数）、candidate count（候选数量）和运行时间。它只输出 `current` 和 `current_provenance`，或者输出带有限 reason（原因）的 `status=unknown`；不会输出 task text（任务正文）、session path（任务记录路径）或 thread identifier（任务编号）。

Deterministic routing path（确定性路由路径）只处理有限的 structured task profile（结构化任务画像）：

```text
由宿主或用户提供的任务特征
  -> 严格 JSON 验证
  -> 确定性路由候选
  -> 仅建议决策或任务继续门槛
```

原始任务正文永远不会进入 deterministic router（确定性路由器）。

获得授权的 Codex Desktop continuation（Codex 桌面端任务继续）使用独立 host orchestration path（宿主编排路径）处理去除调用词后的原始任务：

```text
去除调用词后的原始任务
  + 来自 CODEX_THREAD_ID 的当前源任务
  -> 在本机派生 source_binding_sha256
  -> SHA-256 指纹绑定
  -> 每个外部操作前创建原子预留
  -> 一个目标派生任务
  -> 一次宿主消息发送
  -> 目标任务回读与指纹确认
  -> 导航
  -> 可选的源任务归档
```

原始任务必须发送给 destination task（目标任务），因为目标任务需要执行用户请求；它不会写入 routing profile（路由画像）、telemetry（遥测）或公开 project log（项目日志）。

## 允许的 router data（路由数据）

- task kind（任务类型）、scope（范围）、risk（风险）和 priority（优先级）等有限 enum value（枚举值）；
- architecture signal（架构信号）和 parallel workstream（并行工作流）等非负 count（计数）；
- 表示已独立确认任务特征的 boolean（布尔值）；
- host-declared Model ID（宿主声明的模型编号）和 thinking value（思考档位）；
- 有范围的 provenance timestamp（来源时间戳）和 integrity hash（一致性指纹）；
- host capability presence（宿主能力存在性）与 schema compatibility result（字段契约兼容结果）。

Current-setting provenance source（当前设置来源）可以是 `host_current_setting` 或 `local_session_turn_context`。后者只表示 evidence method（证据方法），不会泄露 session content（任务记录内容）。

## 有限 transfer data（转移数据）

Transfer state（转移状态）可以临时保存：

- `source_binding_sha256`，它根据当前源任务的有效 `CODEX_THREAD_ID` 在本机派生，不会持久保存或输出原始编号；
- `transfer_id`；
- `prompt_sha256`，即 cleaned prompt（去除调用词后的原始任务）的指纹，以及 `router_input_sha256`，即每次 resumed transition（恢复执行的状态转换）都复用的精确 bounded router input（有边界的路由输入）指纹；
- `route_authorization`，即使用同一份 bounded router input（有边界的路由输入）重新运行 deterministic router（确定性路由器）后重新计算的 route authorization（路由授权）；
- `recommended_model` 和 `recommended_thinking`，即 destination setting（目标任务设置）；
- `authorization_binding`，它会绑定 `source_binding_sha256`、`transfer_id`、`prompt_sha256`、`router_input_sha256`、`route_authorization`、`recommended_model` 和 `recommended_thinking`；
- host（宿主）返回的一个 destination task ID（目标任务编号）；
- ordered confirmed event（有序确认事件）、uncertainty reason（不确定原因），以及绑定事件顺序与 event-specific confirmation data（事件专用确认数据）的 `state_chain_sha256`；
- canonical `pending_reservation`（规范待确认预留），其中包含 event（事件）、reservation digest（预留指纹）、lease digest（租约指纹）和 prior chain digest（此前链指纹），直到该事件被确认；
- 每个 external event（外部事件）对应一个 local reservation marker（本机预留标记），其中只包含 hash（指纹）和有限 transfer metadata（转移元数据），例如 `transfer_id`、event（事件）、destination binding（目标任务绑定）、必要时的 prompt digest（任务指纹）、必要时的 delivery setting（发送设置）和 lease digest（租约指纹）。

`transfer_state.py` 会把每次转移放入根据 `source_binding_sha256` 派生的 per-source lock（按源任务锁）和 canonical namespace（规范命名空间）。该 hash（哈希值）会进入 receipt（回执）、`authorization_binding`、reservation marker（预留标记）和每次 transition validation（状态转换验证）。

`transfer_state.py --reserve-event` 会使用 atomic `O_EXCL` creation（原子排他创建）写入 owner-only reservation marker（仅所有者可访问的预留标记），并把对应 `pending_reservation` 持久写入 canonical receipt（规范回执）。默认 durable private root（持久私有根目录）是 `$CODEX_HOME/state/auto-route-for-codex`；`AUTO_ROUTE_STATE_HOME` 只用于明确的 owner-controlled override/test hook（所有者控制的覆盖或测试入口）。只有 reservation winner（预留胜出者）会获得原始 `reservation_lease`；marker（标记）和 receipt（回执）只保存其 digest（指纹）。Matching confirmation（匹配的确认）必须通过 `--reservation-lease` 回传 lease（租约）。Marker（标记）和 receipt（回执）不保存 raw task text（原始任务正文），只留在本机，不是 telemetry（遥测）、repository content（仓库内容）或 release-package content（发行封装内容）。返回授权前，file update（文件更新）和新建 directory update（目录更新）都会完成 `fsync`。

原始 lease（租约）是 ephemeral coordination nonce（一次性协调随机值）和 bearer capability（持有即有权确认的能力），不是 credential（凭据）。它只会在胜出操作的 private local CLI stdout（私有本机命令行标准输出）或等价 tool-execution detail（工具执行明细）中输出一次，再通过 process argument（进程参数）`--reservation-lease` 回传；未来兼容传输方式也可以使用 stdin（标准输入）。它必须留在该私有操作内部，不得复制到 task prompt（任务提示）、final 或其他 user-facing prose（用户可见文字）、package/repository file（封装或仓库文件）、external telemetry（外部遥测）、Issue/support report（问题或支持报告）或 durable log（持久日志）。这种处理能降低意外泄露，但不能防御 malicious same-user writer（同一用户权限下的恶意写入者）。

在 `prompt_delivery_confirmed` 时，Adapter（适配器）必须确认实际传给 destination（目标任务）的 `model` 和 `thinking`。缺少这些值或它们与已绑定 recommendation（建议）不同时，receipt（回执）不会接受 delivery confirmation（发送确认）。

## Integrity and threat boundary（完整性与威胁边界）

每次创建 receipt（回执）或执行 resumed transition（恢复执行的状态转换）都要求 live current-source context（实时当前源任务上下文）。Routing（路由）还要求 `host_capabilities.source_task_context=true`；声明的能力门槛与运行时 `CODEX_THREAD_ID` evidence（证据）两者都必须存在。

每次创建 receipt（回执）和 resumed transition（恢复执行的状态转换）都会复用同一份 bounded router input（有边界的路由输入）并重新计算 route authorization（路由授权）。`authorization_binding` 可以发现 transfer（转移）、prompt digest（任务指纹）、router input（路由输入）、authorization（授权）或 recommended destination setting（推荐目标任务设置）发生变化。`state_chain_sha256` 可以发现 confirmation order（确认顺序）不一致，并按适用情况绑定 destination（目标任务）、prompt digest（任务指纹）、delivery setting（发送设置）和 uncertainty data（不确定数据）。

一个源任务只能拥有一个 canonical transfer（规范转移），因此修改 `transfer_id` 无法绕过 replay protection（重放保护）。另一个源任务的 live `CODEX_THREAD_ID` 会派生不同绑定，因此不能恢复、确认或归档该转移。Archive confirmation（归档确认）前会执行同样验证。源任务上下文缺失、格式错误或不匹配时会 fail closed（证据不足即停止）。

Reservation（预留）会关闭 stale-receipt replay gap（旧回执重放缺口）：只有一个 atomic creator（原子创建者）获得 `side_effect_authorized=true` 和原始 winner-only `reservation_lease`（仅胜出者获得的预留租约）；其他调用方都会得到 `reconcile_required`，必须检查已知操作，而不是 retry（重试）。Canonical receipt（规范回执）会保留 `pending_reservation`，因此删除或丢失 marker（标记）也不能让重复 reserve（预留）再次获得授权。

Evidence TTL（证据有效期）控制新的 authorization（授权）：expired/stale evidence（已过期证据）不能授权新的 reservation（预留）。如果 immutable binding（不可变绑定）有效时，reservation（预留）已经持久记录为 `pending_reservation`，即使后来超过 TTL，匹配 lease（租约）仍只能确认这一项精确操作或把它标记为 `uncertain`；不能授权另一个 host side effect（宿主副作用）。`transfer_state.py` CLI（命令行接口）是唯一受支持的 state-mutation interface（状态修改接口）；通过 Python import（Python 导入）调用内部实现或直接修改 state file（状态文件）都不受支持。

这些 SHA-256 value（SHA-256 值）提供 deterministic integrity（确定性完整性），不是 digital signature（数字签名）或 issuer authentication（签发者认证）。它们假设 local Adapter（本机适配器）和 Reducer（状态归约器）会执行该 contract（契约）。可以同时替换 receipt（回执）和对应 router input（路由输入）的 malicious local writer（恶意本机写入者）能够制造内部一致的替代内容，因此不在公开 threat boundary（威胁边界）内。

## 禁止导出的数据

- fixture（测试样例）、receipt（回执）或仓库文件中的真实用户 prompt（任务正文）或任务历史；
- 个人 repository path（仓库路径）或专有文件内容；
- 真实 Codex task ID（Codex 任务编号）；
- cookie（登录信息）、credential（凭据）、access key（访问密钥）或 authentication header（认证头）；
- local session file（本机任务记录）、runtime log（运行日志）或 browser profile（浏览器资料）；
- `$CODEX_HOME/state/auto-route-for-codex` 或 `AUTO_ROUTE_STATE_HOME` 下的 local reservation marker（本机预留标记）、canonical receipt（规范回执）或原始 reservation lease（预留租约）；
- private model catalog（私有模型目录）或 local marketplace configuration（本机插件市场配置）。

未知 router field（路由字段）会被拒绝，而不是静默忽略。

## 联网与 host side effect（宿主副作用）

Deterministic router（确定性路由器）、fallback reader（后备读取器）和 transfer reducer（转移状态归约器）都没有 telemetry client（遥测客户端）或 credential store（凭据存储）。Fallback reader（后备读取器）会在 `$CODEX_HOME/sessions` 下执行有限 local file read（本机文件读取）；transfer reducer（转移状态归约器）只在 `$CODEX_HOME/state/auto-route-for-codex` 或明确配置的 `AUTO_ROUTE_STATE_HOME` 中写入 local reservation marker（本机预留标记）和 canonical receipt（规范回执）。从 GitHub 安装会由 Codex 或 Git 下载仓库内容。执行完整 Desktop continuation（桌面端任务继续）时，native Codex host tool（Codex 宿主原生工具）负责派生、消息发送、回读、导航和归档；这些 side effect（副作用）继续受宿主及用户现有权限约束。

Explicit plugin activation（显式插件激活）不会给目标任务授予新的文件、联网、发布、credential（凭据）、付款或其他权限。

## Public export control（公开导出控制）

源码项目通过 allowlist-only export（仅允许清单导出）构建公开仓库。Exporter（导出器）会拒绝未知源文件、symlink（符号链接）、个人 path（路径）、类似 UUID 的 task ID（任务编号）、local session data（本机任务记录数据）、reservation marker（预留标记）、配置的私有指纹和常见 secret value（机密值）模式。扫描能降低误泄露概率，但不能替代人工 Release review（发行复核）。
