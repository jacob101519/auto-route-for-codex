---
translation_of: docs/architecture.md
source_revision: docs-v0.5.0-alpha.2
last_synced_version: 0.5.0-alpha.2
---

# 架构

[English](../../../docs/architecture.md)

## 设计目标

公开版把有隐私边界的 task profile（任务画像）转换为 deterministic setting recommendation（确定性设置建议）。在受支持的 Codex Desktop host（Codex 桌面端宿主）中，它也可以通过 fork（派生任务）继续因 `quality` 或 `parallelism` 不匹配的任务，但必须先通过相互独立的 capability check（能力检查）和 evidence check（证据检查）。对于新的 route/reservation（路由或预留），缺少能力、不支持推荐设置或 evidence（证据）为 `unknown|stale|uncertain` 时，结果会降级为 advisory `stay` decision（仅建议保留决策）。已经持久存在的 pending operation（待确认操作）遵守下文单独的 TTL completion rule（有效期完成规则）。

Router（路由器）分开处理四个决定：

1. `model_role`：`deep`、`balanced` 或 `throughput`；
2. `thinking`：由 live host（当前宿主）声明支持的 reasoning value（推理档位）；
3. `topology`：`single`、`single_deep` 或 `parallel`；
4. transfer（转移）：`none` 或受到 capability gate（能力门槛）保护的 `fork`。

## 组成部分

```text
显式调用
  -> 有隐私边界的任务画像
  -> 宿主注入的当前设置
     -> 宿主证据缺失时使用有限本机后备读取
  -> 当前设置、模型目录和宿主能力验证
  -> 确定性路由候选
     -> 仅建议并保留当前任务
     -> 或进入桌面端任务继续门槛
          -> 原子预留事件并持久写入待确认状态
          -> 执行一次宿主副作用
          -> 使用胜出者专属预留租约确认事件
          -> 对派生、发送、回读、导航和归档重复该过程
```

- `SKILL.md` 定义 explicit activation（显式激活）、continuation gate（任务继续门槛）和 no-retry boundary（禁止自动重试边界）。
- `read_current_setting.py` 只在缺少 host-injected current-setting evidence（宿主注入的当前设置证据）时提供 bounded local session fallback（有限本机任务记录后备读取）；它只输出 `current` 和 `current_provenance`，或者返回 `unknown`。
- `router-input.schema.json` 拒绝未知字段和没有边界的任务正文。
- `route_task.py` 先执行 validation（验证），再应用 routing policy（路由政策）。
- `router-output.schema.json` 只接受合法的 `stay` 和 `reroute` tuple（组合）。
- `transfer-receipt.schema.json` 把一次已授权 transfer（转移）、一个 destination（目标任务）、去除调用词后的 prompt digest（任务指纹）、推荐的 destination setting（目标任务设置）、持久 `pending_reservation`（待确认预留），以及每个合法 state/field combination（状态/字段组合）绑定在一起。
- `transfer_state.py` 会在创建 receipt（回执）前以及每次 resumed transition（恢复执行的状态转换）前，使用同一份 bounded router input（有边界的路由输入）重新运行 deterministic router（确定性路由器）。每个 host side effect（宿主副作用）前，它会在默认 `$CODEX_HOME/state/auto-route-for-codex` durable private root（持久私有根目录）或明确指定的 `AUTO_ROUTE_STATE_HOME` 下创建一个 atomic `O_EXCL` reservation（原子排他预留），持久写入对应的 `pending_reservation`，并返回 winner-only `reservation_lease`（仅胜出者获得的预留租约）。
- `validate_contracts.py` 检查 positive/negative/cross-field invariant（正向、负向与跨字段不变量）。
- `verify_public_repo.py` 检查 package（封装）、translation（翻译）、privacy marker（隐私标记）和 link（链接）。

## 决策与执行边界

Router output（路由输出）只是 policy candidate（政策候选），不是调用 native task tool（原生任务工具）的权限。Orchestration layer（编排层）必须在转移前重新检查 live surface（当前使用界面）、tool schema（工具字段契约）、current setting（当前设置）、model catalog（模型目录）、受支持的 Model ID（模型编号）和 thinking value（思考档位）。Current-setting evidence（当前设置证据）优先使用 host-injected observation（宿主注入观测）；只有缺少该证据时，bounded fallback（有限后备读取器）才可以使用 `CODEX_THREAD_ID` 和 `CODEX_HOME`。Routing（路由）还要求 `host_capabilities.source_task_context=true`。此外，无论当前设置证据来自哪里，每次 transfer（转移）都必须有有效的当前源任务 `CODEX_THREAD_ID`。Declared gate（声明门槛）和 runtime evidence（运行时证据）两者缺一不可。Fallback（后备读取器）返回 `unknown`，或源任务上下文缺失、非法、不匹配时，都不能授权 transfer（转移）。

只有通过验证且 `benefit=quality|parallelism` 的 mismatch（不匹配）可以使用：

```text
reroute + quality|parallelism + fork + archive_after_continuation_ready
```

`efficiency` mismatch（效率不匹配）不会自动转移，而是保持：

```text
stay + efficiency + none + keep
```

## Receipt integrity and resume contract（回执完整性与恢复执行契约）

Canonical bounded router input（规范化且有边界的路由输入）是 transfer contract（转移契约）的一部分。创建 receipt（回执）和每次 resumed transition（恢复执行的状态转换）都必须传入同一份 input（输入）。Reducer（状态归约器）接受状态转换前，会验证现有 receipt（回执）、重新运行 deterministic router（确定性路由器）、重新计算 route authorization（路由授权），并拒绝 input digest（输入指纹）、route（路由）或 recommended setting（推荐设置）发生变化的情况。

`authorization_binding` 是以下字段规范化内容的 SHA-256 digest（SHA-256 指纹）：

- `source_binding_sha256`；
- `transfer_id`；
- `prompt_sha256`；
- `router_input_sha256`；
- `route_authorization`；
- `recommended_model`；
- `recommended_thinking`。

这样可以防止同一份 receipt（回执）被静默复用于不同的 prompt（任务正文）、router input（路由输入）、route decision（路由决策）、transfer（转移）或 destination setting（目标任务设置）。在 `prompt_delivery_confirmed` 时，Adapter（适配器）还必须提供实际传给 destination（目标任务）的 `model` 和 `thinking`。它们必须分别等于 `recommended_model` 和 `recommended_thinking`；缺少或不同的值会进入 `uncertain`。

`state_chain_sha256` 从 `authorization_binding` 开始，按顺序绑定每个 confirmed event（确认事件）。Event binding（事件绑定）包含 destination identifier（目标任务编号）、发送与回读确认所需的 prompt digest（任务指纹），以及发送任务时实际传入的 Model（模型）和 thinking（思考档位）。进入 `uncertain` 时还会绑定 uncertainty reason（不确定原因）。

`transfer_state.py` 会从有效的当前源任务 `CODEX_THREAD_ID` 本机派生 `source_binding_sha256`，但不会持久保存或输出原始源任务编号。该 hash（指纹）会进入 per-source lock key（按源任务锁键）、canonical receipt（规范回执）、`authorization_binding`、每个 reservation marker（预留标记）和每次状态转换验证。同一源任务不能用不同 `transfer_id` 启动第二次转移，错误源任务不能恢复、确认或归档该转移；archive confirmation（归档确认）前也会再次核对同一源绑定。

这些 hash（指纹）提供 deterministic integrity（确定性完整性），不是 digital signature（数字签名）。当 Adapter（适配器）和 Reducer（状态归约器）遵守契约时，它们可以暴露不一致的 input（输入）、authorization field（授权字段）、destination setting（目标任务设置）和 event order（事件顺序）；但不能认证 issuer（签发者），也不能防御可以同时替换 receipt（回执）及其 input（输入）的 malicious local writer（恶意本机写入者）。该角色不在公开 threat boundary（威胁边界）内。

每个 external operation（外部操作）都有独立 reservation（预留），它由 `transfer_id`、此前的 `state_chain_sha256` 和 event-specific bounded metadata（事件专用有限元数据）确定。Atomic `O_EXCL` creation（原子排他创建）只允许一个调用方获得 `side_effect_authorized=true` 和原始 winner-only `reservation_lease`（仅胜出者获得的预留租约）。返回前，Reducer（状态归约器）会把 `pending_reservation` 持久写入 canonical receipt（规范回执），其中包含 reservation digest（预留指纹）、lease digest（租约指纹）、event（事件）和 prior chain digest（此前链指纹）。Marker（标记）存在或 canonical receipt（规范回执）仍处于 pending（待确认）状态时，重复 reserve（预留）都会返回 `reconcile_required` 和 `side_effect_authorized=false`；即使 marker（标记）缺失，也不能重新授权已经记录为 pending（待确认）的操作。Matching `--event` confirmation（匹配的事件确认）必须通过 `--reservation-lease` 提供原始 lease（租约），但持久状态只保存其 digest（指纹）。Marker（标记）和 receipt（回执）都属于 private runtime state（私有运行状态），不保存 raw task text（原始任务正文），也不进入 package（封装）或 repository（仓库）。Reducer（状态归约器）会对 marker file（标记文件）和 receipt file（回执文件）执行 `fsync`，并在创建 state directory（状态目录）或替换 canonical receipt（规范回执）后对 parent directory（父目录）执行 `fsync`。`AUTO_ROUTE_STATE_HOME` 只用于明确的 owner-controlled override/test hook（所有者控制的覆盖或测试入口），并且不得在进行中的 transfer（转移）内切换 root（根目录）。

原始 `reservation_lease` 是 ephemeral coordination nonce（一次性协调随机值）和 bearer capability（持有即有权确认的能力），不是 credential（凭据）。胜出的 `transfer_state.py --reserve-event` process（进程）只会在 private local CLI stdout（私有本机命令行标准输出）或等价 tool-execution detail（工具执行明细）中输出一次；Adapter（适配器）再通过 process argument（进程参数）`--reservation-lease` 回传，未来兼容接口也可以改用 stdin（标准输入）。它必须留在该私有操作内部，不得复制到 task prompt（任务提示）、final 或其他 user-facing prose（用户可见文字）、package/repository file（封装或仓库文件）、external telemetry（外部遥测）、Issue/support report（问题或支持报告）或 durable log（持久日志）。这能降低意外泄露风险，但不能防御 malicious same-user writer（同一用户权限下的恶意写入者）。

Evidence freshness（证据新鲜度）只控制新的 reservation authorization（预留授权），不阻止已经持久开始的操作完成。Expired/stale evidence（已过期证据）不能授权新的 reserve（预留）。如果 immutable binding（不可变绑定）有效时，reservation（预留）已持久记录为 `pending_reservation`，即使后来超过 evidence TTL（证据有效期），匹配 lease（租约）也只能确认这一项精确操作或把它标记为 `uncertain`；不能授权另一个 host side effect（宿主副作用）。`transfer_state.py` CLI（命令行接口）是唯一受支持的 state-mutation interface（状态修改接口）。通过 Python import（Python 导入）调用 Reducer（状态归约器）实现或直接修改 state file（状态文件）都属于 unsupported internals（不受支持的内部用法）。

在 lifecycle（生命周期）内，每个 side effect（副作用）都必须在同一个有效 source context（源任务上下文）下执行。只有目标任务发送、回读、导航均确认，而且 archive-time validation（归档时验证）再次确认同一源绑定后，才允许归档源任务。

## Transfer lifecycle（转移生命周期）

State sequence（状态顺序）是单向的：

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

每个 fork/send/readback/navigation/archive side effect（派生、发送、回读、导航或归档副作用）前，Adapter（适配器）都必须预留对应 event（事件）。只有 `side_effect_authorized=true` 时才可以调用 host（宿主）；随后必须保留返回的 winner-only `reservation_lease`（仅胜出者获得的预留租约），再使用 `--event`、`--reservation-lease` 和同一 `--router-input` 确认结果。Prompt delivery（任务发送）还必须提供 `--observed-model` 和 `--observed-thinking`。只有 exact destination readback（精确目标任务回读）证明去除调用词后的原始任务已经到达、prompt delivery（任务发送）确认实际 destination setting（目标任务设置），并且 navigation（导航）成功后，才允许 archive（归档）源任务。目标任务开始后，源任务不得执行原始请求。

任何 timeout（超时）、ambiguous result（不明确结果）、destination mismatch（目标任务不一致）、prompt-digest mismatch（任务指纹不一致）或 incomplete result（不完整结果）都会进入 `uncertain`。在 `uncertain` 中，不得 resend（重复发送）、refork（再次派生）、在源任务中执行原始请求或归档源任务。已知 `destination_thread_id` 时，只能回读该目标任务进行 reconciliation（对账）。如果 fork（派生任务）实际成功，但 host response（宿主响应）在返回任何 destination identifier（目标任务编号）前丢失，durable replay protection（持久重放保护）仍会阻止 refork（再次派生）、源任务执行和源任务归档，但 Plugin（插件）无法自行发现未知目标任务。请保持源任务可见，并通过 host UI（宿主界面）或 support channel（支持渠道）定位或恢复目标任务。这能防止 duplicate execution（重复执行），但不能证明 zero lost tasks（零任务丢失）。

## Trust boundary（信任边界）

Router（路由器）不会自行发现 Model（模型）或 task tool（任务工具）。live host（当前宿主）提供受支持的 Model（模型）和 thinking（思考档位），并暴露可能存在的 Desktop task capability（桌面端任务能力）。Integrity hash（完整性指纹）会把 observation（观测）、transfer authorization（转移授权）、destination setting（目标任务设置）和 ordered state（有序状态）绑定在一起；它不能认证 issuer（签发者），不能替代 execution-layer recheck（执行层重新检查），也不能防御 malicious local writer（恶意本机写入者）。

Bounded fallback reader（有限后备读取器）只接受精确 `CODEX_THREAD_ID`，并在 `$CODEX_HOME/sessions` 下执行 owner/permission/symlink/file-size/record-count/time limit（所有者、权限、符号链接、文件大小、记录数量和时间限制）检查；它不会返回 task text（任务正文）、path（路径）或 thread identifier（任务编号）。Transfer state（转移状态）使用独立的 `$CODEX_HOME/state/auto-route-for-codex` durable subtree（持久子目录）或明确的 `AUTO_ROUTE_STATE_HOME`；marker（标记）和 receipt（回执）只包含 hash（指纹）和有限 transfer metadata（转移元数据），并排除在 package（封装）和 repository（仓库）之外。任务正文仍不会进入 deterministic router（确定性路由器）。获得授权的 task continuation（任务继续）必须由 host orchestration layer（宿主编排层）把去除调用词后的原始任务发送给目标 fork（派生任务）。

## Surface boundary（使用界面边界）

完整路径只适用于字段契约兼容的 Codex Desktop surface（Codex 桌面端使用界面）。Codex CLI（Codex 命令行工具）、IDE（集成开发环境）、cloud（云端）、API（接口）和其他 Agent integration（智能体集成）默认只提供 recommendation（建议），除非它们独立实现并验证等价 contract（契约）。仅安装 package（封装）不能证明 native task tool（原生任务工具）存在。
