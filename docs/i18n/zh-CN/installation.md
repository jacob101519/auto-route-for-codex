---
translation_of: docs/installation.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# 安装、升级、卸载与回退

[English](../../../docs/installation.md)

## 安装固定 Release（发行版）

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

安装后新建 Codex task（Codex 任务），让 host（宿主）刷新 Plugin catalog（插件目录）。选择 **Auto Route for Codex** 或调用 `$auto-route-for-codex`。

## 验证

```sh
codex plugin marketplace list
codex plugin list
```

安装标识应为 `auto-route-for-codex@jacob101519`。安装成功只证明 package（封装）已经被发现，不能证明当前 host（宿主）一定提供某个 Model（模型）。

## 升级

```sh
codex plugin marketplace upgrade jacob101519
codex plugin remove auto-route-for-codex@jacob101519
codex plugin add auto-route-for-codex@jacob101519
```

更换固定 Git ref（Git 引用）前，请先阅读 Release notes（发行说明）。

## 卸载

```sh
codex plugin remove auto-route-for-codex@jacob101519
codex plugin marketplace remove jacob101519
```

卸载只会移除 Plugin selection surface（插件选择入口）。公开版从不修改 Model default（模型默认值）或归档任务，因此没有这些持久状态需要恢复。

## 回退

先移除当前 marketplace entry（插件市场入口），再通过 `--ref` 指定之前的 Release tag（发行标签）重新添加仓库。重新安装 Plugin（插件）并新建任务。

## 从 source checkout（源码检出）安装

只用于开发：

```sh
codex plugin marketplace add /absolute/path/to/auto-route-for-codex
codex plugin add auto-route-for-codex@jacob101519
```

信任本机检出前，先运行根目录 README（项目说明）中的全部验证命令。
