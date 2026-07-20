---
translation_of: README.md
source_revision: docs-v0.5.0-alpha.2
last_synced_version: 0.5.0-alpha.2
---

# Auto Route for Codex

**语言：** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | 简体中文 | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Alpha（早期测试）community project（社区项目），不是 OpenAI 官方产品。

Auto Route for Codex 是一个需要 explicit opt-in（明确主动选择）的 Codex Plugin（Codex 插件）。它根据不包含任务正文的 task profile（任务画像），推荐足够使用的 Model role（模型角色）、reasoning effort（推理强度）和 execution topology（执行方式）。在受支持的 Codex Desktop host（Codex 桌面端宿主）中，只有通过 host capability gate（宿主能力门槛）和 evidence gate（证据门槛）后，它才会把因 `quality` 或 `parallelism` 不匹配的任务通过 fork（派生任务）继续；其他环境会安全降级为在当前任务中提供 recommendation（建议）。

## 为什么需要它

Model choice（模型选择）和 reasoning effort（推理强度）是两个不同决定。短任务如果风险高，仍可能需要更强 Model（模型）；长期、重复且容易验证的任务，可能更适合速度更快的 Model（模型）。本项目把这些取舍变成可检查规则，同时不会静默修改 persistent setting（持久设置）。

公开 contract（契约）遵守六条规则：

- 只有通过 `$auto-route-for-codex` 才会 explicit activation（显式激活）；
- deterministic router（确定性路由器）只接收已枚举的 profile field（任务画像字段）；
- current setting（当前设置）优先使用 host-injected evidence（宿主注入证据）；缺少该证据时，有限的 `read_current_setting.py` fallback（后备读取器）只能输出 `current` 和 `current_provenance`，任何 `unknown` 结果都保持 recommendation-only（仅建议）；
- task continuation（任务继续）必须同时具备 Codex Desktop（Codex 桌面端）、全部必需 task tool（任务工具）、已验证的 current-setting evidence（当前设置证据）与 model-catalog evidence（模型目录证据），并且推荐的 `model` 和 `thinking` 受宿主支持；
- routing（路由）要求 `host_capabilities.source_task_context=true`，每次 transfer（转移）还必须独立获得有效的 `CODEX_THREAD_ID`；`transfer_state.py` 只在本机派生 `source_binding_sha256`，不会持久保存或输出原始 source identifier（源任务编号）；
- 每个 `fork -> send -> readback -> navigate -> archive` side effect（副作用）都必须拥有独立 atomic reservation（原子预留）；只有同一目标任务的整个确认顺序成功后，才允许 archive（归档）源任务。

## 快速开始

前提：

- 当前 Codex surface（Codex 使用界面）支持 Plugin（插件）和 explicit Skill invocation（显式技能调用）；
- `PATH` 中可以运行 Codex CLI（Codex 命令行工具）；
- 可以访问公开 Git repository（Git 仓库）。

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.2
codex plugin add auto-route-for-codex@jacob101519
```

新建 Codex task（Codex 任务），选择 **Auto Route for Codex**，或者输入：

```text
$auto-route-for-codex 请检查这个任务，并使用足够完成任务的 Codex 设置。
```

Plugin（插件）始终返回带版本的 decision（决策），并优先使用 host-injected current setting（宿主注入的当前设置）。缺少该 observation（观测）且 `CODEX_THREAD_ID` 与可用的 `CODEX_HOME` 同时存在时，`read_current_setting.py` 只会检查匹配的 local session（本机任务记录），并输出有限的 `current + current_provenance`，不会输出 task text（任务正文）、path（路径）或 thread identifier（任务编号）；读取失败会返回 `unknown`。在具备完整能力的 Codex Desktop host（Codex 桌面端宿主）中，已验证的 `quality` 或 `parallelism` mismatch（不匹配）可以通过 fork（派生任务）使用推荐的 `model` 和 `thinking` 继续。`efficiency` mismatch（效率不匹配）、不受支持的 surface（使用界面）、缺少工具、不受支持的设置或 `unknown|stale|uncertain` evidence（未知、过期或不确定证据）都保持 `stay`，只提供 recommendation-only（仅建议）。符合条件的 transfer tuple（转移组合）包含 `fork + archive_after_continuation_ready`。

Plugin（插件）不会修改 native model picker（原生模型选择器）、`config.toml`、persistent default（持久默认值）、sandbox setting（沙箱设置）、approval policy（审批政策）、network access（联网权限）或 credential（凭据）。

每次 transfer（转移）都使用 source-task binding（源任务绑定）：routing-time host evidence（路由时宿主证据）必须声明 `host_capabilities.source_task_context=true`，运行时还必须提供有效的 `CODEX_THREAD_ID`，两者缺一不可。`transfer_state.py` 只在本机派生 `source_binding_sha256`，不会持久保存或输出原始 source identifier（源任务编号）。该 hash（哈希值）会进入 per-source lock key（按源任务锁键）、canonical receipt（规范回执）、`authorization_binding`、reservation marker（预留标记）以及包括 archive confirmation（归档确认）在内的每次状态验证。因此，同一源任务不能借助不同 `transfer_id` 再启动一次转移，错误源任务也不能恢复、确认或归档该转移；源任务上下文缺失、非法或不匹配时会 fail closed（证据不足即停止）。

## 受能力门槛保护的 Desktop continuation（桌面端任务继续）

只有以下检查全部通过，full path（完整路径）才可使用：

1. 当前 surface（使用界面）是 Codex Desktop（Codex 桌面端）；
2. host（宿主）提供字段契约兼容的 `fork_thread`、`send_message_to_thread`、`read_thread`、`navigate_to_codex_page` 和 `set_thread_archived` capability（能力）；
3. current-setting evidence（当前设置证据）为 `verified` 且仍有效，并优先来自 host injection（宿主注入），只有必要时才使用有限 fallback（后备读取器）；model-catalog evidence（模型目录证据）也必须为 `verified` 且仍有效；
4. 推荐的 `model` 和 `thinking` 均受 live host（当前宿主）支持；
5. 每次 fork/send/readback/navigation/archive call（派生、发送、回读、导航或归档调用）前，`transfer_state.py --reserve-event` 都会创建 atomic `O_EXCL` marker（原子排他预留标记），并在 canonical receipt（规范回执）中持久写入 `pending_reservation`；只有胜出的调用方会获得 `side_effect_authorized=true` 和原始 `reservation_lease`；
6. 每次 confirmation（确认）都必须通过 `--reservation-lease` 回传该 lease（租约）；prompt delivery（任务发送）还会确认实际使用的 Model（模型）与 thinking override（思考档位覆盖值），destination readback（目标任务回读）会证明去除调用词后的原始任务已到达精确 fork（派生任务），并且成功打开目标任务后才产生 archive authorization（归档授权）。

固定 lifecycle（生命周期）为：

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

成功创建 reservation（预留）后，先执行 host side effect（宿主副作用），再通过 `--event`、`--reservation-lease` 和同一 `--router-input` 完成 confirmation（确认）；`prompt_delivery_confirmed` 还必须提供 `--observed-model` 和 `--observed-thinking`。Canonical receipt（规范回执）会持久保存带 lease digest（租约指纹）的 `pending_reservation`。Marker（标记）存在或 receipt（回执）仍处于 pending（待确认）状态时，重复 reserve（预留）都会返回 `reconcile_required` 和 `side_effect_authorized=false`；即使 marker（标记）缺失，也不会重新授权 side effect（副作用）。默认 durable private state root（持久私有状态根目录）是 `$CODEX_HOME/state/auto-route-for-codex`；`AUTO_ROUTE_STATE_HOME` 只用于明确的 owner-controlled override/test hook（所有者控制的覆盖或测试入口）。Reservation marker（预留标记）与 receipt（回执）只包含 hash（指纹）和有限 transfer metadata（转移元数据），不保存 raw task text（原始任务正文）。返回授权前，marker write（标记写入）、receipt write（回执写入）和新建 state directory（状态目录）都会完成 `fsync`。

`reservation_lease` 是 ephemeral coordination nonce（一次性协调随机值）和 bearer capability（持有即有权确认的能力），不是 credential（凭据）。它只会在胜出操作的 private local CLI stdout（私有本机命令行标准输出）或等价 tool-execution detail（工具执行明细）中输出一次，再通过 process argument（进程参数）`--reservation-lease` 回传；未来兼容接口也可以改用 stdin（标准输入）。它必须留在该私有操作内部，不得复制到 task prompt（任务提示）、final 或其他 user-facing prose（用户可见文字）、package（封装）、repository（仓库）、external telemetry（外部遥测）、Issue/support report（问题或支持报告）或 durable log（持久日志）。这能减少意外泄露，但不能防御 malicious same-user writer（同一用户权限下的恶意写入者）。

Expired/stale evidence（已过期证据）绝不能授权新的 reservation（预留）。如果 immutable binding（不可变绑定）有效时已经把 reservation（预留）持久记录为 `pending_reservation`，即使后来超过 evidence TTL（证据有效期），匹配 lease（租约）仍可以只确认这一项已开始操作，或把它标记为 `uncertain`；不能据此授权新的 host side effect（宿主副作用）。唯一受支持的 state mutation interface（状态修改接口）是 `transfer_state.py` CLI（命令行接口）。通过 Python import（Python 导入）调用内部实现或直接修改 state file（状态文件）都属于 unsupported internals（不受支持的内部用法）。

任何 timeout（超时）、mismatch（不一致）、incomplete result（不完整结果）或 ambiguous side effect（不明确副作用）都会进入 `uncertain`。此时不得 resend（重复发送）、refork（再次派生）、在源任务中执行原始请求或归档源任务。已知 destination identifier（目标任务编号）时，只能对账该目标任务。如果 fork（派生任务）实际成功，但 host response（宿主响应）在返回任何 destination identifier（目标任务编号）前丢失，durable replay protection（持久重放保护）仍会阻止 refork（再次派生）、源任务执行和源任务归档，但 Plugin（插件）无法自行发现未知目标任务。请保持源任务可见，并通过 host UI（宿主界面）或 support channel（支持渠道）定位或恢复目标任务。这能防止 duplicate execution（重复执行），但不能证明 zero lost tasks（零任务丢失）。Receipt/reservation hash（回执与预留指纹）提供 deterministic integrity（确定性完整性），不是 signature（数字签名）；能够替换本机状态的 malicious local writer（恶意本机写入者）不在 threat boundary（威胁边界）内。

## 公开版安全边界

包含：

- 严格的 JSON input/output/transfer-receipt schema（JSON 输入、输出与转移回执契约）；
- deterministic routing（确定性路由）、bounded current-setting fallback（有限当前设置后备读取）和 reservation-backed transfer-state logic（预留保护的转移状态逻辑）；
- privacy-preserving source-task binding（保护隐私的源任务绑定），它会阻止错误源任务恢复转移，也会阻止同一源任务使用多个 `transfer_id`；
- 受 capability gate（能力门槛）保护的 Codex Desktop continuation contract（Codex 桌面端任务继续契约）；
- route test（路由测试）、contract test（契约测试）、semantic-negative test（语义负向测试）、state-machine test（状态机测试）和 failure-boundary test（失败边界测试）；
- repository/privacy/translation/release verification（仓库、隐私、翻译与发行验证）；
- English authoritative documentation（英文权威文档）、完整 Simplified Chinese translation（简体中文翻译）和多语言 README entry point（项目说明入口）。

刻意不包含：

- unbounded session scanning（无边界任务记录扫描）、task-text extraction（任务正文提取），或者导出 session content（任务记录内容）、reservation marker（预留标记）、canonical receipt（规范回执）或原始 reservation lease（预留租约）；
- private current-setting receipt（私有当前设置回执）、private catalog（私有模型目录）或 local marketplace state（本机插件市场状态）；
- runtime log（运行日志）、credential（凭据）、个人 path（路径）、真实 task ID（任务编号）或 private configuration（私有配置）；
- hidden invocation（隐藏调用）、针对 `efficiency` 的自动转移、自动修改 native model picker（原生模型选择器）或写入 Codex global configuration（Codex 全局配置）；
- 宣称 Codex CLI（Codex 命令行工具）、IDE（集成开发环境）、cloud（云端）、API（接口）或其他 Agent（智能体）具备 Codex Desktop task tool（Codex 桌面端任务工具）。

进一步阅读：[隐私与数据流](docs/i18n/zh-CN/privacy-and-data-flow.md)、[路由政策](docs/i18n/zh-CN/routing-policy.md)和[兼容性](docs/i18n/zh-CN/compatibility.md)。

## 仓库结构

| path | 用途 |
|---|---|
| `.codex-plugin/plugin.json` | Plugin manifest（插件清单） |
| `.agents/plugins/marketplace.json` | Marketplace entry（插件市场入口） |
| `skills/auto-route-for-codex/` | Skill（技能）、schema（字段契约）、bounded current-setting reader（有限当前设置读取器）、Router（路由器）、reservation-backed transfer reducer（预留保护的转移状态归约器）和测试 |
| `docs/` | English authoritative documentation（英文权威文档） |
| `docs/i18n/zh-CN/` | 完整 Simplified Chinese translation（简体中文翻译） |
| `scripts/verify_public_repo.py` | repository/translation/privacy/link check（仓库、翻译、隐私和链接检查） |
| `scripts/build_release.py` | 生成 deterministic Plugin ZIP（确定性插件压缩包）和 `SHA256SUMS` |

## 从 clean clone（干净克隆）验证

```sh
python3 -m pip install --disable-pip-version-check --only-binary=:all: --require-hashes -r .github/requirements-ci.txt
python3 scripts/verify_public_repo.py --require-git-history
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

本地检查通过只能证明 package contract（封装契约）和 modeled state transition（模拟状态转移）成立，不能证明每个 Codex Desktop host version（Codex 桌面端宿主版本）的真实 side effect（副作用）都成功；真实 E2E behavior（端到端行为）仍取决于当前宿主。请查看[兼容性](docs/i18n/zh-CN/compatibility.md)。

## 文档

- [架构](docs/i18n/zh-CN/architecture.md)
- [安装、升级、卸载与回退](docs/i18n/zh-CN/installation.md)
- [配置契约](docs/i18n/zh-CN/configuration.md)
- [隐私与数据流](docs/i18n/zh-CN/privacy-and-data-flow.md)
- [路由政策](docs/i18n/zh-CN/routing-policy.md)
- [兼容性](docs/i18n/zh-CN/compatibility.md)
- [故障排查](docs/i18n/zh-CN/troubleshooting.md)
- [常见问题](docs/i18n/zh-CN/faq.md)

## 当前状态

`v0.5.0-alpha.2` 加固 public-history privacy（公开历史隐私）、CI dependency integrity（持续集成依赖完整性）和 Release provenance（发布来源证明）；runtime routing contract（运行时路由契约）不变。请查看 [CHANGELOG.md](CHANGELOG.md) 和 [ROADMAP.md](ROADMAP.md)。

## 贡献与安全

提交 Pull Request（拉取请求）前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请按照 [SECURITY.md](SECURITY.md) 使用 GitHub private vulnerability reporting（GitHub 私密漏洞报告），不要在公开 Issue（问题）中暴露敏感细节。

## License（许可证）

Apache License 2.0，详见 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。
