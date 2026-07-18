---
translation_of: README.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# Auto Route for Codex

[English](README.md) | [简体中文](README.zh-CN.md)

> Alpha（早期测试）社区项目，不是 OpenAI 官方产品。

Auto Route for Codex 是一个需要显式选择的 Codex Plugin（Codex 插件）。它根据不包含任务正文的 task profile（任务画像），推荐足够使用的 Model role（模型角色）、reasoning effort（推理强度）和 execution topology（执行方式）。公开版刻意只提供 recommendation（建议）：不会 fork（派生）、创建、导航、归档或重复执行任务。

## 为什么需要它

Model（模型）和 reasoning effort（推理强度）是两个不同决定。短任务如果风险高，仍可能需要更强 Model（模型）；长期、重复且容易验证的任务，可能更适合速度更快的 Model（模型）。本项目把这些取舍变成可检查的规则，同时避免把模型选择变成看不见的 side effect（副作用）。

公开 contract（契约）遵守四条规则：

- 只有通过 `$auto-route-for-codex` 才会显式激活；
- deterministic router（确定性路由器）只接收枚举、计数和布尔值；
- recommendation（建议）只能解析到 host（宿主）声明支持的 Model（模型）和 thinking（思考档位）；
- 所有公开 decision（决策）都保持 `stay + none|efficiency + none + keep`。

## 快速开始

前提：

- 当前 Codex surface（Codex 使用界面）支持 Plugin（插件）和显式 Skill（技能）调用；
- `PATH` 中可以运行 Codex CLI（Codex 命令行工具）；
- 可以访问公开 Git repository（Git 仓库）。

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

新建 Codex task（Codex 任务），选择 **Auto Route for Codex**，或者输入：

```text
$auto-route-for-codex 请检查这个任务，并推荐足够使用的 Codex 设置。
```

Plugin（插件）会返回带版本的 recommendation（建议），但不会修改当前任务的 Model（模型）或设置。

## 公开版安全边界

包含：

- 严格的 JSON input/output schema（JSON 输入输出契约）；
- deterministic routing logic（确定性路由逻辑）；
- recommendation-only tests（仅建议测试）和 semantic negative cases（语义负向用例）；
- repository/release verification scripts（仓库与发行验证脚本）；
- 英文权威原文和完整简体中文翻译。

刻意不包含：

- local session reader（本机任务记录读取器）；
- 私有 current-setting receipt（当前设置回执）或 model catalog（模型目录）；
- fork、navigation、archive 和 replay orchestration（派生、导航、归档与重放编排）；
- runtime log（运行日志）、credential（凭据）、本机路径、任务编号或私有配置；
- 自动切换 Model（模型）或写入 Codex 全局配置。

进一步阅读：[隐私与数据流](docs/i18n/zh-CN/privacy-and-data-flow.md)和[路由政策](docs/i18n/zh-CN/routing-policy.md)。

## 仓库结构

| path | 用途 |
|---|---|
| `.codex-plugin/plugin.json` | Plugin manifest（插件清单） |
| `.agents/plugins/marketplace.json` | Marketplace entry（插件市场入口） |
| `skills/auto-route-for-codex/` | Skill（技能）、schema（字段契约）、Router（路由器）和测试 |
| `docs/` | English authoritative documentation（英文权威文档） |
| `docs/i18n/zh-CN/` | 完整简体中文翻译 |
| `scripts/verify_public_repo.py` | 仓库、翻译、隐私和链接检查 |
| `scripts/build_release.py` | 生成确定性 Plugin ZIP（插件压缩包）和 `SHA256SUMS` |

## 从 clean clone（干净克隆）验证

```sh
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

本地检查通过只能证明 repository contract（仓库契约）成立，不能证明所有 Codex host（Codex 宿主）都提供相同的 Plugin（插件）或 Model（模型）界面。请查看[兼容性](docs/i18n/zh-CN/compatibility.md)。

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

`v0.4.0-alpha.1` 是第一个 public alpha（公开早期测试版）。在 stable release（稳定版）之前，API（接口）和 package layout（封装结构）可能变化。请查看 [CHANGELOG.md](CHANGELOG.md) 和 [ROADMAP.md](ROADMAP.md)。

## 贡献与安全

提交 Pull Request（拉取请求）前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请按照 [SECURITY.md](SECURITY.md) 使用 GitHub private vulnerability reporting（GitHub 私密漏洞报告），不要在公开 Issue（问题）中暴露敏感细节。

## License（许可证）

Apache License 2.0，详见 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。
