---
translation_of: docs/installation.md
source_revision: docs-v0.5.0-alpha.2
last_synced_version: 0.5.0-alpha.2
---

# 安装、升级、卸载与回退

[English](../../../docs/installation.md)

## 安装固定 Release（发行版）

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.2
codex plugin add auto-route-for-codex@jacob101519
```

安装后新建 Codex task（Codex 任务），让 host（宿主）刷新 Plugin catalog（插件目录）。选择 **Auto Route for Codex** 或调用 `$auto-route-for-codex`。

## 验证 discovery（发现状态）

```sh
codex plugin marketplace list
codex plugin list
```

安装标识应为 `auto-route-for-codex@jacob101519`。Discovery（发现成功）只能证明 package（封装）可见，不能证明 Model（模型）可用、evidence（证据）已验证、Desktop task tool（桌面端任务工具）兼容或 task continuation（任务继续）成功。

## 验证 source package（源码封装）

从 clean clone（干净克隆）运行：

下面带 hash lock（哈希锁定）的 Python 3.12 / Linux package（软件包）仅用于 repository verification（仓库验证）和 release check（发行检查），不是 Plugin runtime dependency（插件运行依赖）。

```sh
python3 -m pip install --disable-pip-version-check --only-binary=:all: --require-hashes -r .github/requirements-ci.txt
python3 -B scripts/verify_public_repo.py --require-git-history
python3 -B -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 -B skills/auto-route-for-codex/scripts/validate_contracts.py
python3 -B scripts/build_release.py --output-dir dist
```

这些检查验证 deterministic policy（确定性政策）、schema（字段契约）、bounded current-setting reader（有限当前设置读取器）、reservation-backed transfer state（预留保护的转移状态）、privacy rule（隐私规则）、translation（翻译）和 release package（发行封装），不能替代真实 Codex Desktop E2E check（Codex 桌面端端到端检查）。

## 升级

```sh
codex plugin marketplace upgrade jacob101519
codex plugin remove auto-route-for-codex@jacob101519
codex plugin add auto-route-for-codex@jacob101519
```

更换固定 Git ref（Git 引用）前，请先阅读 Release note（发行说明）。`v0.5.0-alpha.1` 把公开 contract（契约）从 recommendation-only（仅建议）扩展为 capability-gated Codex Desktop continuation（受能力门槛保护的 Codex 桌面端任务继续）。

## 卸载

```sh
codex plugin remove auto-route-for-codex@jacob101519
codex plugin marketplace remove jacob101519
```

卸载只移除 Plugin selection surface（插件选择入口），不会恢复宿主已经归档的源任务、删除目标任务、修改 persistent model default（持久模型默认值），也不会自动清除 `$CODEX_HOME/state/auto-route-for-codex` 或 `AUTO_ROUTE_STATE_HOME` 中的 reservation marker（预留标记）和 canonical receipt（规范回执）。如果 transfer（转移）处于 `uncertain` 或 pending（待确认），请先检查并 reconcile（对账）任务状态再卸载；不要为了强制 retry（重试）而删除 replay-protection state（重放保护状态）。

## 回退

先移除当前 marketplace entry（插件市场入口），再通过 `--ref` 指定之前的 Release tag（发行标签）重新添加仓库。重新安装 Plugin（插件）并新建任务。

回退到 `v0.4.0-alpha.1` 会恢复早期 recommendation-only public behavior（公开版仅建议行为），但不会撤销新版本已经产生的 host task state（宿主任务状态），也不会删除新版本创建的 local reservation marker（本机预留标记）或 canonical receipt（规范回执）。回退前必须 reconcile（对账）任何 `pending_reservation`；marker（标记）缺失不代表可以 retry（重试）。

确认 pending operation（待确认操作）或把它标记为 `uncertain` 时，只能使用 `transfer_state.py` CLI（命令行接口）。通过 Python import（Python 导入）调用内部实现或直接修改 state file（状态文件）都不受支持。Expired evidence（过期证据）不能授权新的 reserve（预留），但如果 immutable binding（不可变绑定）有效时，该 operation（操作）已经持久绑定为 `pending_reservation`，匹配 lease（租约）仍可以在 evidence TTL（证据有效期）到期后只完成这一项操作。

## 从 source checkout（源码检出）安装

只用于开发：

```sh
codex plugin marketplace add /absolute/path/to/auto-route-for-codex
codex plugin add auto-route-for-codex@jacob101519
```

信任本机检出前，先运行全部 verification command（验证命令）。不要使用 dirty（有未提交修改）或未审查的检出执行具备 archive capability（归档能力）的 E2E test（端到端测试）。
