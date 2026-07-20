---
translation_of: docs/troubleshooting.md
source_revision: docs-v0.5.0-alpha.1
last_synced_version: 0.5.0-alpha.1
---

# 故障排查

[English](../../../docs/troubleshooting.md)

## 看不到 Plugin（插件）

1. 运行 `codex plugin marketplace list`。
2. 运行 `codex plugin list`。
3. 确认安装标识是 `auto-route-for-codex@jacob101519`。
4. 新建 Codex task（Codex 任务），让 host（宿主）刷新 Plugin catalog（插件目录）。

## 调用没有反应

Skill（技能）只允许 opt-in（主动选择）。请选择 **Auto Route for Codex**，或在任务开头输入 `$auto-route-for-codex`。引用或 delegated text（委派文字）中的字面 token（调用词）不会激活它。

## Recommendation（建议）是 unresolved（未解析）

这是 fail-closed behavior（证据不足即停止）的正常行为。请检查 live host（当前宿主）是否声明了一致且受支持的 Model（模型）、thinking value（思考档位）和 role mapping（角色映射），并确认必需 current-setting evidence（当前设置证据）与 model-catalog evidence（模型目录证据）仍然有效。Host-injected current setting（宿主注入的当前设置）优先。缺少该证据时，bounded fallback（有限后备读取器）需要有效 `CODEX_THREAD_ID`、安全的 `CODEX_HOME` session tree（任务记录目录树）和唯一可读的匹配 session（任务记录）；任何失败都会返回 `unknown`，不会暴露 task text（任务正文）、path（路径）或 thread identifier（任务编号）。

## 任务留在源任务中

缺少任何 continuation requirement（任务继续要求）时，这是预期行为。常见原因包括：

- surface（使用界面）不是 Codex Desktop（Codex 桌面端）；
- 一个或多个必需 task tool（任务工具）不存在或 schema-incompatible（字段契约不兼容）；
- route benefit（路由收益）是 `none` 或 `efficiency`；
- current-setting evidence（当前设置证据）或 model-catalog evidence（模型目录证据）为 `unknown`、`stale` 或 `uncertain`；
- 推荐的 Model（模型）或 thinking value（思考档位）不受支持；
- execution-time recheck（执行时重新检查）与 route candidate（路由候选）不一致；
- `host_capabilities.source_task_context` 不是 `true`，或 `CODEX_THREAD_ID` 缺失、格式错误，或与 canonical transfer receipt（规范转移回执）绑定的源任务不一致。

如果有足够 routing information（路由信息），Plugin（插件）仍应提供 advisory recommendation（建议）。

`CODEX_THREAD_ID` 有两个不同作用。Current-setting fallback（当前设置后备读取）只在缺少 host-injected current-setting evidence（宿主注入的当前设置证据）时使用它。Transfer source binding（转移源任务绑定）则要求每次转移都提供它，routing（路由）还会独立要求 `host_capabilities.source_task_context=true`。Reducer（状态归约器）会在本机把运行时编号哈希为 `source_binding_sha256`，不会写入或输出原始编号。Declared gate（声明的能力门槛）和 runtime evidence（运行时证据）两者都必须存在。

## Transfer（转移）报告 source binding error（源任务绑定错误）

`source_thread_context_required` 表示 live `CODEX_THREAD_ID` 缺失或无效。`state_file_missing` 通常表示当前源任务派生了另一个 per-source namespace（按源任务命名空间），因此该位置没有 canonical receipt（规范回执）；这是 wrong-source（错误源任务）最常见的结果。`source_binding_mismatch` 表示已加载 receipt（回执）中的绑定与 live source binding（实时源任务绑定）冲突，应将其视为被移动、伪造或损坏的 state（状态）。`source_task_already_bound` 表示该源任务已通过另一个 `transfer_id` 拥有转移。不要修改或伪造 `CODEX_THREAD_ID`，不要新建另一个 `transfer_id`，不要移动或编辑 receipt（回执），也不要重试 side effect（副作用）。返回原始源任务，对账其现有转移。错误源任务不能恢复、确认或归档该转移。

## Reservation（预留）提示需要 reconcile（对账）

`reconcile_required` 与 `side_effect_authorized=false` 表示精确 event（事件）的 atomic marker（原子标记）已经存在，或 canonical receipt（规范回执）仍包含 `pending_reservation`；external operation（外部操作）可能已经开始。不要删除 marker（标记）或 receipt（回执），也不要重复 fork/send/readback/navigation/archive call（派生、发送、回读、导航或归档调用）。Marker（标记）缺失不会清除 pending receipt（待确认回执），也不会恢复授权。已知 destination identifier（目标任务编号）时，请先对账该 destination（目标任务）和 last confirmed receipt state（最后确认的回执状态）。如果没有返回 destination identifier（目标任务编号），不得 refork（再次派生）；请保持源任务可见，并按照下方 timeout recovery guidance（超时恢复指引）处理。

Reservation state（预留状态）使用默认 `$CODEX_HOME/state/auto-route-for-codex` durable root（持久根目录）。`AUTO_ROUTE_STATE_HOME` 只用于明确的 owner-controlled override/test hook（所有者控制的覆盖或测试入口）；在 active transfer（进行中的转移）和 reconciliation（对账）完成前，必须保持选定 root（根目录）不变。Current-setting fallback（当前设置后备读取器）仍只读取 `$CODEX_HOME/sessions`。成功的 reserve output（预留输出）包含 winner-only `reservation_lease`（仅胜出者获得的预留租约），matching `--event` confirmation（匹配的事件确认）必须通过 `--reservation-lease` 回传它；lease（租约）缺失或不匹配不代表可以 retry（重试）。返回授权前，marker（标记）、receipt（回执）和新建 directory（目录）的更新都会完成 `fsync`。

该 lease（租约）是 ephemeral coordination nonce（一次性协调随机值）和 bearer capability（持有即有权确认的能力），不是 credential（凭据）。它只会在 private local CLI stdout（私有本机命令行标准输出）或等价 tool-execution detail（工具执行明细）中输出一次，再通过 process argument（进程参数）`--reservation-lease` 回传；未来兼容接口也可以使用 stdin（标准输入）。不得把它复制到 task prompt（任务提示）、final 或其他 user-facing prose（用户可见文字）、package/repository content（封装或仓库内容）、external telemetry（外部遥测）、Issue/support report（问题或支持报告）或 durable log（持久日志）。Malicious same-user writer（同一用户权限下的恶意写入者）仍不在这个保护边界内。

Evidence（证据）过期后不得再次 reserve（预留）。如果 immutable binding（不可变绑定）有效时，reservation（预留）已经持久记录为 `pending_reservation`，即使后来超过 evidence TTL（证据有效期），匹配 lease（租约）仍可以只确认这项操作或把它标记为 `uncertain`；不能授权另一个 side effect（副作用）。所有状态修改都必须使用 `transfer_state.py` CLI（命令行接口）。通过 Python import（Python 导入）调用内部实现或直接编辑 marker/receipt file（标记或回执文件）都不受支持，还可能破坏 reconciliation evidence（对账证据）。

## 目标任务开始了，但源任务仍可见

不要手动再次调用 Plugin（插件），也不要重复发送原始请求。Transfer（转移）可能处于 `uncertain`，或者 destination readback/navigation/archive（目标任务回读、导航或归档）尚未确认。先对已经知道的目标任务进行 reconciliation（对账）。保留源任务比 premature archive（过早归档）更安全。

## 源任务已经归档

只有 destination delivery/readback/navigation（目标任务送达、回读与导航）全部确认后，archive（归档）才是预期行为。请在目标任务中继续。如果目标任务不包含原始请求，应把它视为 security-sensitive premature-archive defect（安全敏感的过早归档缺陷），并通过私密渠道报告。

## Tool call（工具调用）超时

不要通过建立另一个目标任务重试。可能产生 side effect（副作用）的调用超时后，transfer（转移）会进入 `uncertain`；reservation（预留）会继续提供 replay protection（重放保护）。已知 destination task ID（目标任务编号）时，只能通过该目标任务进行 reconciliation（对账）。如果 fork（派生任务）实际成功，但 host response（宿主响应）在返回任何 destination identifier（目标任务编号）前丢失，replay protection（重放保护）仍会阻止 refork（再次派生）、源任务执行和源任务归档，但 Plugin（插件）无法自行发现未知目标任务。请保持源任务可见，并通过 host UI（宿主界面）或 support channel（支持渠道）定位或恢复目标任务。这不能证明 zero lost tasks（零任务丢失）。

## Repository verification（仓库验证）失败

```sh
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
```

先修复第一个 invariant（不变量）错误。Release（发行）时不得绕过 translation（翻译）、privacy（隐私）、manifest（清单）、schema（字段契约）或 transfer-state check（转移状态检查）。

## 需要更多帮助

使用 GitHub Discussions（GitHub 讨论）咨询用法；使用对应 Issue template（问题模板）报告可复现故障。请提供 version（版本）、Codex surface（Codex 使用界面）、capability-gate result（能力门槛结果）、decision tuple（决策组合）、last confirmed transfer state（最后确认的转移状态）、不含本机 path（路径）或 task identifier（任务编号）的 reservation status（预留状态），以及经过清理的 verification output（验证输出）。安全问题使用 GitHub private vulnerability reporting（GitHub 私密漏洞报告）。
