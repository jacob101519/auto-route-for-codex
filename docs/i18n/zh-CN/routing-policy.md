---
translation_of: docs/routing-policy.md
source_revision: docs-v0.5.0-alpha.2
last_synced_version: 0.5.0-alpha.2
---

# 路由政策

[English](../../../docs/routing-policy.md)

## Minimum sufficient setting（最低充分设置）

Router（路由器）会推荐 policy（政策）认为足以完成当前 task profile（任务画像）的最低 host-declared setting（宿主声明设置），而不是默认认为越强越好。

## Model role（模型角色）

- `deep`：需求模糊、高风险、架构、研究或最终决策任务；
- `balanced`：常规实现和中等范围分析；
- `throughput`：目标清楚、重复、低风险且容易客观验证的任务。

具体 Model ID（模型编号）只来自 live host role mapping（当前宿主角色映射）。

## Reasoning effort（推理强度）

Reasoning effort（推理强度）和 Model role（模型角色）分开判断。清楚的局部任务可以使用较低档；multi-stage（多阶段）、high-risk（高风险）或 weakly verifiable（难验证）的任务会提高档位。Router（路由器）不会发明 host（宿主）没有声明支持的档位。

## Topology（执行方式）

`parallel` 必须同时满足：

- 存在几个有意义且相互独立的 workstream（工作流）；
- coupling（耦合）足够低；
- 可以独立 verification（验证）；
- write-conflict risk（写冲突风险）可接受；
- 已取得 explicit delegation authorization（明确委派授权）；
- 存在 independently observed parallelism evidence（独立观测的并行证据）。

Permission（权限）本身不能证明并行事实存在。

## 合法 decision tuple（决策组合）

公开 contract（契约）只接受：

```text
stay + none + none + keep
stay + efficiency + none + keep
reroute + quality + fork + archive_after_continuation_ready
reroute + parallelism + fork + archive_after_continuation_ready
```

对于新的 route/reservation（路由或预留），`unknown|stale|uncertain` evidence（未知、过期或不确定证据）一律降级为 `stay + none + none + keep`。已经持久存在的 `pending_reservation` 遵守下文单独的 TTL completion rule（有效期完成规则）。`efficiency` benefit（效率收益）不会自动转移，因为仅为节省额度或延迟而建立新任务，可能消耗更多时间和 Token（令牌）。

## Capability gate（能力门槛）

`reroute` output（重新路由输出）只是 candidate（候选）。Codex Desktop orchestration layer（Codex 桌面端编排层）必须立即验证：

- 当前 surface（使用界面）是 Codex Desktop（Codex 桌面端）；
- 所有必需 task tool（任务工具）存在且 schema（字段契约）兼容；
- current-setting evidence（当前设置证据）为 `verified` 且仍有效，并优先使用 host injection（宿主注入），只有缺少宿主证据时才使用 bounded local fallback（有限本机后备读取）；
- model-catalog evidence（模型目录证据）为 `verified` 且仍有效；
- 推荐的 `model` 和 `thinking` 受支持；
- route evidence（路由证据）仍与 execution-time observation（执行时观测）一致；
- routed host evidence（已路由宿主证据）中存在 `host_capabilities.source_task_context=true`，并且 transfer time（转移时）独立存在有效的 live current-source `CODEX_THREAD_ID`（实时当前源任务编号）。

任何检查失败时，不得执行 native task side effect（原生任务副作用），recommendation（建议）保持 advisory（仅建议）。

## Receipt-bound authorization（回执绑定的授权）

创建 receipt（回执）和每次 resumed transition（恢复执行的状态转换）都必须复用同一份 canonical bounded router input（规范化且有边界的路由输入）。Reducer（状态归约器）接受下一个 event（事件）前，会重新运行 deterministic router（确定性路由器）并重新计算 authorization（授权）；只携带 caller-supplied authorization string（调用方提供的授权字符串）或 receipt（回执）而不提供这份 input（输入）是不够的。

`authorization_binding` 会绑定以下所有字段：

- `source_binding_sha256`；
- `transfer_id`；
- `prompt_sha256`；
- `router_input_sha256`；
- `route_authorization`；
- `recommended_model`；
- `recommended_thinking`。

在 `prompt_delivery_confirmed` 时，Adapter（适配器）必须提供实际传给 destination（目标任务）的 `model` 和 `thinking`。只有它们分别精确匹配 `recommended_model` 和 `recommended_thinking` 时，confirmation（确认）才会成功；缺少或不匹配的值会因 destination-setting mismatch（目标任务设置不匹配）进入 `uncertain`。

`state_chain_sha256` 会把 `authorization_binding` 与 ordered confirmation event（有序确认事件）、destination（目标任务）、需要核对的 prompt digest（任务指纹）、发送任务时的实际设置，以及任何 terminal uncertainty reason（终态不确定原因）绑定在一起。重新排序、遗漏、回退或不一致的 confirmation state（确认状态）都会被拒绝。

Reducer（状态归约器）会根据当前源任务的有效 `CODEX_THREAD_ID` 在本机派生 `source_binding_sha256`，不会持久保存或输出原始源任务编号。该 hash（哈希值）会进入 per-source lock key（按源任务锁键）、canonical receipt（规范回执）、`authorization_binding`、每个 reservation marker（预留标记）和每次 transition validation（状态转换验证）。同一源任务不能使用另一个 `transfer_id` 启动第二次转移；另一个源任务不能恢复、确认或归档第一次转移。源任务上下文缺失、无效或不匹配时会 fail closed（证据不足即停止）。`host_capabilities.source_task_context=true` 声明与运行时证据两者都必须存在，不能相互替代。

这些 binding（绑定）是 deterministic integrity check（确定性完整性检查），不是 digital signature（数字签名）。它们不能认证 Adapter（适配器），也不能防御可以同时替换 receipt（回执）和 bounded router input（有边界的路由输入）的 malicious local writer（恶意本机写入者）；该角色不在 threat boundary（威胁边界）内。

每个 fork/send/readback/navigation/archive side effect（派生、发送、回读、导航或归档副作用）前，Adapter（适配器）都必须使用当前 receipt（回执）和同一 `--router-input` 调用 `transfer_state.py --reserve-event`。Reservation creation（预留创建）会在默认 `$CODEX_HOME/state/auto-route-for-codex` durable root（持久根目录）或明确的 `AUTO_ROUTE_STATE_HOME` 下使用 atomic `O_EXCL` file（原子排他文件）。胜出的 reserve（预留）会把 `pending_reservation` 持久写入 canonical receipt（规范回执），并返回 `side_effect_authorized=true` 与原始 winner-only `reservation_lease`（仅胜出者获得的预留租约）。只有该调用方可以执行 host call（宿主调用），而 matching `--event` confirmation（匹配的事件确认）必须通过 `--reservation-lease` 回传 lease（租约）。Marker（标记）存在或 receipt（回执）仍处于 pending（待确认）状态时，重复 reserve（预留）都会返回 `reconcile_required`；即使 marker（标记）缺失也一样。返回授权前，marker（标记）、receipt（回执）和新建 state directory（状态目录）的更新都会完成 `fsync`。必须 reconcile（对账）该操作，不得 retry（重试）。

原始 lease（租约）是 ephemeral coordination nonce（一次性协调随机值）和 bearer capability（持有即有权确认的能力），不是 credential（凭据）。胜出的 private local CLI（私有本机命令行）或等价 tool execution（工具执行）只输出一次，Adapter（适配器）再通过 process argument（进程参数）`--reservation-lease` 回传；未来兼容接口也可以使用 stdin（标准输入）。它必须留在该操作内部，不得复制到 task prompt（任务提示）、final 或其他 user-facing prose（用户可见文字）、package/repository content（封装或仓库内容）、external telemetry（外部遥测）、Issue/support report（问题或支持报告）或 durable log（持久日志）。该规则不能防御 malicious same-user writer（同一用户权限下的恶意写入者）。

Stale evidence（过期证据）绝不能授权新的 reserve（预留）。如果 immutable binding（不可变绑定）有效时，reservation（预留）已经持久记录为 `pending_reservation`，即使后来超过 evidence TTL（证据有效期），匹配 lease（租约）也只能确认这一项已开始操作或把它标记为 `uncertain`；不能授权另一个 host side effect（宿主副作用）。状态修改只能使用 `transfer_state.py` CLI（命令行接口）；Python import（Python 导入）和直接修改 state file（状态文件）属于 unsupported internals（不受支持的内部用法）。

## Ordered continuation（有序任务继续）

对一个合法 candidate（候选）只能执行一次固定顺序：

1. 使用同一份 bounded router input（有边界的路由输入）重新运行 Router（路由器），只有 verified fork decision（已验证的派生决策）仍成立时才创建 receipt（回执）；
2. 预留 `fork_created`；只有 reservation winner（预留胜出者）可以使用 same-directory environment（相同目录环境）建立 fork（派生任务），随后用返回的 `--reservation-lease`、`--event fork_created` 和同一份 bounded router input（有边界的路由输入）确认；
3. 使用 prompt digest（任务指纹）与实际 `model` 和 `thinking` 预留 `prompt_delivery_confirmed`；只有 reservation winner（预留胜出者）可以只发送一次任务，随后使用返回的 `--reservation-lease`、同一 `--router-input`、`--observed-model` 和 `--observed-thinking` 通过 `--event prompt_delivery_confirmed` 确认；
4. 预留 `destination_readback_confirmed`；只有 reservation winner（预留胜出者）可以回读精确目标任务、验证 cleaned-prompt digest（任务指纹），再用返回的 `--reservation-lease` 和同一 input（输入）确认 event（事件）；
5. 预留 `navigation_confirmed`；只有 reservation winner（预留胜出者）可以导航到同一目标任务，再用返回的 `--reservation-lease` 和同一 input（输入）确认 event（事件）；
6. `archive_authorized=true` 后先再次验证同一 live source binding（实时源任务绑定），再预留 `source_archive_confirmed`；只有 reservation winner（预留胜出者）可以归档源任务，再用返回的 `--reservation-lease` 和同一 input（输入）确认 event（事件）。

不得建立不相关的 fresh task（独立新任务）、使用移动同一任务状态的 handoff（移交），也不得 fallback（后备切换）到第二个目标任务。

目标任务开始后，源任务不得执行原始请求。

## Failure policy（失败政策）

Timeout（超时）、incomplete result（不完整结果）、ambiguous result（不明确结果）、wrong destination（目标任务错误）或 prompt mismatch（任务不一致）都会进入 `uncertain`：

- 不得 resend（重复发送）或 refork（再次派生）；
- 不得在源任务中执行原始请求；
- 不得归档源任务；
- 已知 destination identifier（目标任务编号）时，只能回读该目标任务进行 reconciliation（对账）。

如果 fork（派生任务）实际成功，但 host response（宿主响应）在返回任何 destination identifier（目标任务编号）前丢失，durable replay protection（持久重放保护）仍会阻止 refork（再次派生）、源任务执行和源任务归档，但 Plugin（插件）无法自行发现未知目标任务。请保持源任务可见，并通过 host UI（宿主界面）或 support channel（支持渠道）定位或恢复目标任务。这能防止 duplicate execution（重复执行），但不能证明 zero lost tasks（零任务丢失）。

重复 confirmed event（确认事件）是 idempotent（幂等）的；state jump（状态跳跃）、backtracking（回退）和 automatic retry（自动重试）都会被拒绝。已存在的 marker（标记）或 canonical `pending_reservation`（规范待确认预留）表示 external action（外部动作）可能已经开始，不是重复执行该动作的授权。Marker（标记）缺失不会清除 pending receipt（待确认回执），也不会恢复授权。
