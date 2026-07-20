---
translation_of: docs/configuration.md
source_revision: docs-v0.5.0-alpha.1
last_synced_version: 0.5.0-alpha.1
---

# 配置

[English](../../../docs/configuration.md)

## 不写入 persistent configuration（持久配置）

Auto Route for Codex 不修改 `config.toml`、native model picker（原生模型选择器）、sandbox setting（沙箱设置）、approval policy（审批政策）、network access（联网权限）、credential（凭据）或 persistent model default（持久模型默认值）。每个任务必须通过显式选择或 `$auto-route-for-codex` 单独激活。

不写 persistent configuration（持久配置）不等于完全没有 local runtime state（本机运行状态）。为了防止 replay（重放），`transfer_state.py --reserve-event` 会在默认 `$CODEX_HOME/state/auto-route-for-codex` durable root（持久根目录）下创建 owner-only atomic reservation marker（仅所有者可访问的原子预留标记）和 canonical receipt（规范回执）。`AUTO_ROUTE_STATE_HOME` 只用于明确的 owner-controlled override/test hook（所有者控制的覆盖或测试入口）。胜出的 reserve（预留）会写入 `pending_reservation`，返回原始 `reservation_lease`，而 matching confirmation（匹配的确认）必须通过 `--reservation-lease` 回传它；持久状态只保存 lease digest（租约指纹）。Marker（标记）、receipt（回执）和新建 state directory（状态目录）都会完成 `fsync`。它们只包含 hash（指纹）和有限 transfer metadata（转移元数据），不包含 configuration（配置）或 raw task text（原始任务正文），也不会复制进 package（封装）或 repository（仓库）。

每次 transfer-state command（转移状态命令）还必须拥有有效的当前源任务 `CODEX_THREAD_ID`。Reducer（状态归约器）只在本机派生 `source_binding_sha256`，将其用于 per-source lock（按源任务锁）和 canonical state namespace（规范状态命名空间），不会写入或输出原始源任务编号。即使 current-setting evidence（当前设置证据）来自 host injection（宿主注入）而无需读取 session（任务记录），转移仍然需要 `CODEX_THREAD_ID`。源上下文缺失、非法或不匹配时会 fail closed（证据不足即停止）。

`reservation_lease` 是 ephemeral coordination nonce（一次性协调随机值）和 bearer capability（持有即有权确认的能力），不是 credential（凭据）。它只会在胜出操作的 private local CLI stdout（私有本机命令行标准输出）或等价 tool-execution detail（工具执行明细）中输出一次，再通过 process argument（进程参数）`--reservation-lease` 回传；未来兼容接口也可以改用 stdin（标准输入）。不得把它复制到 task prompt（任务提示）、final 或其他 user-facing prose（用户可见文字）、package（封装）、repository（仓库）、external telemetry（外部遥测）、Issue/support report（问题或支持报告）或 durable log（持久日志）。这种处理不能防御 malicious same-user writer（同一用户权限下的恶意写入者）。

Expired/stale evidence（已过期证据）不能授权新的 reservation（预留）。如果 reservation（预留）在 immutable binding（不可变绑定）有效时已经持久记录为 `pending_reservation`，即使后来超过 evidence TTL（证据有效期），也可以使用匹配 lease（租约）只确认这项操作或把它标记为 `uncertain`；不能据此授权新的 host side effect（宿主副作用）。只有 `transfer_state.py` CLI（命令行接口）是受支持的 state mutation interface（状态修改接口）。通过 Python import（Python 导入）调用内部实现或直接修改 state file（状态文件）都不受支持。

## Routing input（路由输入）

Deterministic router（确定性路由器）只接收有限的 structured fact（结构化事实），例如：

- `current`：当前 Model（模型）、effort（推理档位）、status（状态）和 observation time（观测时间）；
- `profile`：描述任务的 enum（枚举）、count（计数）和 boolean（布尔值）；
- host-declared model identifier（宿主声明的模型编号）和 thinking value（思考档位）；
- host-provided model-role mapping（宿主提供的模型角色映射）；
- 有时间边界的 catalog provenance（模型目录来源）和 host provenance（宿主来源）；
- routing-time host declaration（路由时宿主声明）`host_capabilities.source_task_context=true`；
- independently observed parallelism（独立观测的并行事实）和 explicit delegation authorization（明确委派授权）。

用户消息、文件内容、repository path（仓库路径）、task ID（任务编号）、credential（凭据）和 session history（任务历史）都不是合法的 router profile field（路由画像字段）。

`current` 优先来自 host-injected observation（宿主注入观测）。缺少该证据时，`read_current_setting.py` 可以使用 `CODEX_THREAD_ID` 和 `$CODEX_HOME/sessions`，在严格 safety limit（安全限制）下只读取匹配的 local session（本机任务记录）。它只贡献 `current` 和 `current_provenance`；失败返回 `unknown`，不能授权 task continuation（任务继续）。`AUTO_ROUTE_STATE_HOME` 只改变 transfer-state root（转移状态根目录），不会改变 current-setting evidence（当前设置证据）的读取位置。

## Recommendation resolution（建议解析）

只有选中的 Model（模型）和 thinking value（思考档位）由 live host（当前宿主）声明支持、逻辑角色映射一致并且必需 evidence（证据）仍在有效期内且内部一致时，recommendation（建议）才可以解析。Router（路由器）不会发明宿主不支持的组合。

Unresolved recommendation（未解析建议）不能授权 task continuation（任务继续）；结果只提供建议并保留源任务。

## Continuation gate（任务继续门槛）

即使 recommendation（建议）已经解析，也不能单独授权 native side effect（原生副作用）。执行前，可信 Codex Desktop orchestration layer（Codex 桌面端编排层）必须验证：

- 当前 surface（使用界面）和必需 task-tool schema（任务工具字段契约）；
- 当前 Model（模型）和 thinking value（思考档位）；
- 当前 model-catalog evidence（模型目录证据）；
- 推荐的 `model` 和 `thinking` 是否受支持；
- 是否存在合法的 `quality` 或 `parallelism` decision（决策）；
- route evidence（路由证据）中是否有 `host_capabilities.source_task_context=true`，并且转移时是否存在有效的当前源任务 `CODEX_THREAD_ID`；
- 是否只有一个精确的 cleaned prompt（去除调用词后的原始任务）和一个精确 destination（目标任务）。
- 是否为精确的下一个 side effect（副作用）创建了 fresh atomic reservation（新的原子预留）、持久 canonical `pending_reservation`（规范待确认预留）和 winner-only `reservation_lease`（仅胜出者获得的预留租约）。

Declared capability gate（声明能力门槛）与 runtime source context（运行时源任务上下文）两者都必须存在，不能互相替代。Execution-layer observation（执行层观测）与 route candidate（路由候选）不一致时，task continuation（任务继续）必须关闭。只有 reservation output（预留输出）包含 `side_effect_authorized=true` 时才可以执行 host side effect（宿主副作用）；confirmation（确认）必须通过 `--reservation-lease` 提供返回的 lease（租约）。返回 `reconcile_required` 时必须 reconcile（对账），不得 retry（重试）；即使 marker（标记）缺失，只要 canonical receipt（规范回执）仍处于 pending（待确认）状态，也必须如此。

## Invocation policy（调用政策）

`allow_implicit_invocation` 为 false。仅在引用、复制或 delegated content（委派内容）中出现插件名称不会激活它。请在 Codex composer（Codex 输入区）选择 Plugin（插件），或在任务开头输入 `$auto-route-for-codex`。

Explicit activation（显式激活）只授权本次 routing decision（路由决策）及其必需 task delegation（任务委派），不会授予新的文件、联网、发布、credential（凭据）、付款或其他权限。
