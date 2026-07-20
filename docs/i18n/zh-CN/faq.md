---
translation_of: docs/faq.md
source_revision: docs-v0.5.0-alpha.1
last_synced_version: 0.5.0-alpha.1
---

# 常见问题

[English](../../../docs/faq.md)

## Plugin（插件）会自动切换当前 Model（模型）吗？

不会。它不修改当前任务的 native model picker（原生模型选择器）或 persistent default（持久默认值）。当通过验证的 Codex Desktop reroute（Codex 桌面端重新路由）符合条件时，它会把推荐的 `model` 和 `thinking` 传给 destination fork（目标派生任务）。

## 它会创建新任务吗？

在字段契约兼容的 Codex Desktop host（Codex 桌面端宿主）中，通过验证的 `quality` 或 `parallelism` mismatch（不匹配）可以通过 fork（派生任务）继续。这是 continuation relationship（任务继续关系），不是互不相关的 fresh task（独立新任务）。`efficiency` decision（效率决策）和不受支持的 surface（使用界面）会留在源任务中。

## 什么时候归档源任务？

只有一个 destination（目标任务）已经派生、去除调用词后的原始任务只使用已确认 destination setting（目标任务设置）发送了一次、destination readback（目标任务回读）确认该任务存在、navigation（导航）成功，并且 archive-time validation（归档时验证）确认仍是同一 source binding（源任务绑定）后，才允许 archive（归档）源任务。每个 external action（外部动作）还必须先获得带 `side_effect_authorized=true` 和 winner-only `reservation_lease`（仅胜出者获得的预留租约）的独立 atomic reservation（原子预留）；matching confirmation（匹配的确认）必须通过 `--reservation-lease` 回传该 lease（租约）。Router decision（路由决策）本身永远不能授权归档。

## Transfer（转移）为什么要求 `CODEX_THREAD_ID`？

它让本机 Reducer（状态归约器）识别当前源任务，但不会被保存或输出。`transfer_state.py` 会派生 `source_binding_sha256`，并把该 hash（哈希值）用于 per-source lock（按源任务锁）、receipt（回执）、authorization binding（授权绑定）、reservation marker（预留标记）和每次 transition check（状态转换检查）。这会阻止同一源任务使用不同 `transfer_id` 再启动转移，也会阻止另一个源任务恢复或归档该转移。源任务上下文缺失、无效或不匹配时会 fail closed（证据不足即停止）。Routing（路由）还要求 `host_capabilities.source_task_context=true`；该声明与运行时 `CODEX_THREAD_ID` evidence（证据）两者都必须存在。Current-setting fallback（当前设置后备读取）是另一种用途：host-injected current-setting evidence（宿主注入的当前设置证据）可以避免读取 `$CODEX_HOME/sessions`，但不会取消转移的 source-binding requirement（源任务绑定要求）。

## Tool call（工具调用）超时怎么办？

Transfer（转移）会进入 `uncertain`；对应 marker（标记）和 canonical receipt（规范回执）会在 `$CODEX_HOME/state/auto-route-for-codex` 或明确的 `AUTO_ROUTE_STATE_HOME` 下继续提供 durable replay protection（持久重放保护）。Plugin（插件）不得 resend（重复发送）、refork（再次派生）、在源任务中重新执行请求或归档源任务。已知 destination identifier（目标任务编号）时，只能对该目标任务进行 reconciliation（对账）。如果 fork（派生任务）实际成功，但 host response（宿主响应）在返回任何 destination identifier（目标任务编号）前丢失，replay protection（重放保护）仍会阻止 refork（再次派生）、源任务执行和源任务归档，但 Plugin（插件）无法自行发现未知目标任务。请保持源任务可见，并通过 host UI（宿主界面）或 support channel（支持渠道）定位或恢复目标任务。这不能证明 zero lost tasks（零任务丢失）。即使 marker（标记）缺失，只要 canonical `pending_reservation`（规范待确认预留）仍存在，就会继续禁止重新授权。

## 为什么公开版现在可以接近本机体验？

可移植的 routing core（路由核心）、bounded current-setting fallback（有限当前设置后备读取器）、transfer schema（转移契约）、reservation-backed state reducer（预留保护的状态归约器）和 safety test（安全测试）都可以公开。Host-injected current setting（宿主注入的当前设置）仍然优先；fallback（后备读取器）只输出 `current` 和 provenance（来源信息），失败时保持 recommendation-only（仅建议）。满足公开 capability gate（能力门槛）的宿主获得完整路径；其他宿主安全降级为 recommendation-only（仅建议）。

## 更高 reasoning effort（推理强度）一定会提高质量吗？

不一定。Router（路由器）会分别考虑质量、延迟、额度消耗、任务风险和 verifiability（可验证性）。

## 它能支持未来 Model（模型）吗？

可以，不需要把未来 Model ID（模型编号）写死在 routing policy（路由政策）中。live host（当前宿主）提供逻辑角色映射和受支持编号；未知组合只提供 advisory recommendation（建议）。

## 其他 AI agent（AI 智能体）能使用吗？

不能直接使用。其他 Agent（智能体）可以实现带版本的 JSON/state-machine contract（JSON 与状态机契约），但必须自行定义并验证 activation（激活）、capability evidence（能力证据）、task relationship（任务关系）和 side-effect boundary（副作用边界）。

## 项目会发送 telemetry（遥测）吗？

没有实现 runtime telemetry（运行时遥测）。Bounded reader（有限读取器）只访问 `$CODEX_HOME/sessions` 下获得 current-setting evidence（当前设置证据）所需的精确 local session（本机任务记录）。Replay protection（重放保护）只在 `$CODEX_HOME/state/auto-route-for-codex` 或 `AUTO_ROUTE_STATE_HOME` 下写入包含 hash（指纹）与 transfer metadata（转移元数据）、不含 raw task text（原始任务正文）的 local reservation marker（本机预留标记）和 canonical receipt（规范回执）。原始 winner-only reservation lease（仅胜出者获得的预留租约）不会持久保存在这些 artifact（制品）中。以上状态都不会作为 telemetry（遥测）传输，也不会进入公开 repository（仓库）。

## `reservation_lease` 是 credential（凭据）吗？它可能出现在哪里？

不是。它是 ephemeral coordination nonce（一次性协调随机值）和 bearer capability（持有即有权确认的能力）。胜出的 private local CLI（私有本机命令行）或等价 tool execution（工具执行）只输出一次，再通过 process argument（进程参数）`--reservation-lease` 回传；未来接口也可以改用 stdin（标准输入）。不得把它复制到 task prompt（任务提示）、final 或其他 user-facing prose（用户可见文字）、package（封装）、repository（仓库）、external telemetry（外部遥测）、Issue/support report（问题或支持报告）或 durable log（持久日志）。这不能防御 malicious same-user writer（同一用户权限下的恶意写入者）。

## Reservation（预留）仍为 pending（待确认）时 evidence TTL（证据有效期）到期怎么办？

Stale evidence（过期证据）不能授权新的 reservation（预留）。如果 immutable binding（不可变绑定）有效时，reservation（预留）已经持久记录为 `pending_reservation`，即使超过 evidence TTL（证据有效期），匹配 lease（租约）仍可以只确认这项已开始操作，或把它标记为 `uncertain`；不能授权新的 host side effect（宿主副作用）。状态修改只能使用 `transfer_state.py` CLI（命令行接口）；Python import（Python 导入）和直接修改 state file（状态文件）不受支持。

## 这是 OpenAI 官方项目吗？

不是，这是 unofficial community project（非官方社区项目）。
