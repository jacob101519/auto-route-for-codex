---
translation_of: README.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# Auto Route for Codex

**語言：** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | 繁體中文 | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Alpha（早期測試）社群專案。不是 OpenAI 官方產品。

Auto Route for Codex 是一個需要明確選擇加入的 Codex Plugin（Codex 外掛程式）。它會根據具備隱私界線的 task profile（任務輪廓），推薦足以完成任務的 model role（模型角色）、reasoning effort（推理強度）和 execution topology（執行拓撲）。公開版刻意只提供 recommendation（建議）：永遠不會派生、建立、導覽、封存或重新執行任務。

## 為什麼需要它

Model choice（模型選擇）和 reasoning effort（推理強度）是兩個不同的決定。短但高風險的任務可能需要更強的 Model（模型），而長期、重複且可驗證的工作可能更適合較快的 Model（模型）。這個 Plugin（外掛程式）會明確呈現這些取捨，同時避免讓模型選擇成為不可見的 side effect（副作用）。

公開 contract（契約）遵循四項規則：

- 只有透過 `$auto-route-for-codex` 才會明確啟用；
- deterministic router（確定性路由器）只會接收列舉的 profile field（輪廓欄位）；
- recommendation（建議）只會解析為 host（宿主）提供的 Model（模型）和 thinking（思考檔位）值；
- 每個公開 decision（決策）都保持 `stay + none|efficiency + none + keep`。

## 快速開始

前置需求：

- 支援 Plugin（外掛程式）和明確 Skill invocation（技能呼叫）的 Codex surface（Codex 使用介面）；
- 可以從 `PATH` 執行 Codex CLI（Codex 命令列工具）；
- 可以存取公開 Git repository（Git 儲存庫）。

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

建立新的 Codex task（Codex 任務），選擇 **Auto Route for Codex**，或輸入：

```text
$auto-route-for-codex 檢查這項任務，並推薦足以完成任務的 Codex 設定。
```

Plugin（外掛程式）會傳回帶有版本的 recommendation（建議），但不會變更目前任務的 Model（模型）或設定。

## 公開版安全界線

包含：

- 嚴格的 JSON input and output schemas（JSON 輸入與輸出結構規範）；
- deterministic routing logic（確定性路由邏輯）；
- 僅提供 recommendation（建議）的測試和 semantic negative cases（語意負向案例）；
- 公開 repository（儲存庫）和 Release（發行版）的驗證腳本；
- English（英文）文件和完整的 Simplified Chinese（簡體中文）文件。

刻意排除：

- 本機 session-file reader（工作階段檔案讀取器）；
- 私有的 current-setting receipt（目前設定回執）或 catalog（目錄）；
- 任務派生、導覽、封存和重新執行編排；
- runtime log（執行階段日誌）、credential（憑證）、本機 path（路徑）、task identifier（任務識別碼）或 private configuration（私有設定）；
- 自動變更 Model（模型）或寫入 Codex global configuration（Codex 全域設定）。

請參閱 [Privacy and data flow](docs/privacy-and-data-flow.md) 和 [Routing policy](docs/routing-policy.md)。

## 儲存庫結構

| Path | 用途 |
|---|---|
| `.codex-plugin/plugin.json` | Plugin manifest（外掛程式資訊清單） |
| `.agents/plugins/marketplace.json` | Marketplace entry（市集項目） |
| `skills/auto-route-for-codex/` | Skill（技能）、schema（結構規範）、Router（路由器）和測試 |
| `docs/` | 權威 English（英文）文件 |
| `docs/i18n/zh-CN/` | 完整的 Simplified Chinese（簡體中文）翻譯 |
| `scripts/verify_public_repo.py` | Repository（儲存庫）、翻譯、隱私和連結檢查 |
| `scripts/build_release.py` | 確定性的 Plugin ZIP（外掛程式壓縮檔）和 `SHA256SUMS` 建置工具 |

## 從乾淨的 Clone 驗證

```sh
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

本機檢查通過，表示 repository contract（儲存庫契約）有效；但無法證明每個 Codex host version（Codex 宿主版本）都提供相同的 Plugin（外掛程式）或 Model surface（模型介面）。請參閱 [Compatibility](docs/compatibility.md)。

## 文件

- [Architecture](docs/architecture.md)
- [Installation and rollback](docs/installation.md)
- [Configuration contract](docs/configuration.md)
- [Privacy and data flow](docs/privacy-and-data-flow.md)
- [Routing policy](docs/routing-policy.md)
- [Compatibility](docs/compatibility.md)
- [Troubleshooting](docs/troubleshooting.md)
- [FAQ](docs/faq.md)

## 專案狀態

`v0.4.0-alpha.1` 是第一個公開 Alpha（早期測試）版本。在 stable release（穩定版本）推出之前，API 和 package layout（套件結構）可能會變更。請參閱 [CHANGELOG.md](CHANGELOG.md) 和 [ROADMAP.md](ROADMAP.md)。

## 貢獻與安全性

建立 pull request（提取要求）之前，請先閱讀 [CONTRIBUTING.md](CONTRIBUTING.md)。請依照 [SECURITY.md](SECURITY.md) 的說明，透過 GitHub private vulnerability reporting（GitHub 私密漏洞回報）提交安全問題；請勿在公開 issue（議題）中發布敏感報告。

## 授權條款

Apache License 2.0。請參閱 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。
