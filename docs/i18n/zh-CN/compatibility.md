---
translation_of: docs/compatibility.md
source_revision: docs-v0.5.0-alpha.1
last_synced_version: 0.5.0-alpha.1
---

# 兼容性

[English](../../../docs/compatibility.md)

Compatibility（兼容性）是时点结论，必须根据当前 Codex host（Codex 宿主）重新检查。

| surface（使用界面） | 公开 Alpha（早期测试）行为 | 要求与说明 |
|---|---|---|
| 提供全部必需 task tool（任务工具）的 Codex Desktop（Codex 桌面端） | 受 capability gate（能力门槛）保护的完整任务继续 | explicit invocation（显式调用）、`host_capabilities.source_task_context=true`、有效的当前源任务 `CODEX_THREAD_ID`、已验证的当前设置与模型目录、兼容的 tool schema（工具字段契约）、受支持的推荐 `model` 和 `thinking`，以及安全可写的 durable transfer state（持久转移状态） |
| 能力或证据不完整的 Codex Desktop（Codex 桌面端） | recommendation-only fallback（仅建议降级） | 不派生、不重复发送、不导航、不归档 |
| Codex CLI（Codex 命令行工具） | recommendation-only（仅建议） | 可能支持插件市场和本地验证，但不假设存在 Desktop task tool（桌面端任务工具） |
| Codex IDE surface（Codex 编辑器界面） | recommendation-only（仅建议），除非另有独立集成 | Plugin discovery（插件发现）与 host control（宿主控制）随版本变化 |
| Codex cloud task（Codex 云任务） | recommendation-only（仅建议） | 可能没有用户模型控制或 Desktop task relationship（桌面端任务关系） |
| OpenAI API（OpenAI 接口）或 Agents SDK（智能体开发包） | 需要独立集成 | 调用方可以实现等价 state machine（状态机），但不能声称存在原生 Desktop continuation relationship（桌面端任务继续关系） |
| 其他 AI agent（AI 智能体） | 不直接支持 | 只能在自行定义 activation（激活）、evidence（证据）和 side-effect policy（副作用政策）后适配 JSON contract（JSON 契约） |

## Full-continuation requirement（完整任务继续要求）

Codex Desktop（Codex 桌面端）完整路径要求执行时同时满足：

- 显式选择 **Auto Route for Codex** 或 `$auto-route-for-codex`；
- routed host evidence（已路由宿主证据）中包含 `host_capabilities.source_task_context=true`，并且存在有效的 live current-source `CODEX_THREAD_ID`（实时当前源任务编号）；两者都必须存在，不能相互替代；
- 存在字段契约兼容的 `fork_thread`、`send_message_to_thread`、`read_thread`、`navigate_to_codex_page` 和 `set_thread_archived` capability（能力）；
- current-setting evidence（当前设置证据）为 `verified` 且仍有效，并优先使用 host injection（宿主注入）；只有缺少宿主证据时才使用有限的 `CODEX_THREAD_ID`/`CODEX_HOME` fallback（后备读取）；
- model-catalog evidence（模型目录证据）为 `verified` 且仍有效；
- 推荐的 `model` 和 `thinking` 由 live host（当前宿主）声明支持；
- 存在合法的 `quality` 或 `parallelism` reroute candidate（重新路由候选）；
- 使用由 owner（所有者）控制的安全 `$CODEX_HOME/state/auto-route-for-codex` storage（存储）或明确的 `AUTO_ROUTE_STATE_HOME`，并支持 atomic `O_EXCL` reservation（原子排他预留）、winner-only reservation lease（仅胜出者获得的预留租约）、持久 `pending_reservation` 和 file/directory fsync（文件与目录同步落盘）；
- archive（归档）前已成功完成 destination delivery/readback/navigation（目标任务送达、回读与导航）。

任何要求为 unavailable（不可用）、stale（过期）、unknown（未知）、uncertain（不确定）或 incompatible（不兼容）时，都不能授权新的 reservation（预留）；源任务保持可见，并只输出 advisory recommendation（建议）。如果 immutable binding（不可变绑定）有效时，reservation（预留）已经持久记录为 `pending_reservation`，即使后来超过 evidence TTL（证据有效期），也可以使用匹配 lease（租约）只确认这项已开始操作或把它标记为 `uncertain`。这条有限 completion path（完成路径）不能授权另一个 host side effect（宿主副作用）。

## Repository requirement（仓库要求）

- repository verification script（仓库验证脚本）需要 Python 3.11 或更高版本；
- 文档中的安装流程需要 Plugin marketplace support（插件市场支持）；
- 每次 transfer（转移）都要求有效 `CODEX_THREAD_ID`；只有需要 current-setting fallback（当前设置后备读取）时，才额外要求安全的 `$CODEX_HOME/sessions` tree（任务记录目录树）；
- reservation-backed continuation（预留保护的任务继续）要求由 owner（所有者）控制、不是 symlink（符号链接）的 `$CODEX_HOME/state/auto-route-for-codex` durable root（持久根目录）或明确的 `AUTO_ROUTE_STATE_HOME`；
- `transfer_state.py` CLI（命令行接口）是唯一受支持的 state-mutation interface（状态修改接口）；Python import（Python 导入）和直接修改 state file（状态文件）不受支持；
- Release verification（发行验证）需要 clean public clone（干净公开克隆）。

## Version policy（版本政策）

当前目标公开版本是 `0.5.0-alpha.1`。Alpha（早期测试）版本可能包含不兼容 contract change（契约变更）。Git tag（Git 标签）、Plugin manifest version（插件清单版本）、Release title（发行标题）和 Release asset name（发行制品名称）必须一致。

## 兼容性不代表什么

安装成功不保证每个账号或宿主都存在某个特定 Model（模型）、thinking value（思考档位）或 native task tool（原生任务工具）。Unit test（单元测试）通过只能证明 deterministic policy（确定性政策）和 modeled state transition（模拟状态转移）成立；只有真实 host E2E run（宿主端到端运行）才能验证 Desktop side effect（桌面端副作用）。
