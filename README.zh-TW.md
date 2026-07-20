---
translation_of: README.md
source_revision: docs-v0.5.0-alpha.1
last_synced_version: 0.5.0-alpha.1
---

# Auto Route for Codex

**語言：** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | 繁體中文 | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Alpha（早期測試）社群專案。不是 OpenAI 官方產品。

Auto Route for Codex 是一個需要 explicit opt-in（明確主動選擇）的 Codex Plugin（Codex 外掛程式）。它會根據具備隱私界線的 task profile（任務輪廓），推薦足以完成任務的 model role（模型角色）、reasoning effort（推理強度）和 execution topology（執行方式）。在支援的 Codex Desktop host（Codex 桌面端宿主）中，只有 host capability gate（宿主能力門檻）與 evidence gate（證據門檻）通過後，才會透過 fork（派生任務）繼續重視 `quality` 或 `parallelism` 的任務。其他環境會安全降級為目前任務中的 recommendation（建議）。

## 為什麼需要它

Model choice（模型選擇）和 reasoning effort（推理強度）是兩個不同的決定。短但高風險的任務可能需要更強的 Model（模型），而長期、重複且可驗證的工作可能更適合較快的 Model（模型）。這個 Plugin（外掛程式）會明確呈現這些取捨，同時避免讓模型選擇成為不可見的 side effect（副作用）。

公開 contract（契約）遵循六項規則：

- 只有透過 `$auto-route-for-codex` 才會明確啟用；
- deterministic router（確定性路由器）只會接收列舉的 profile field（輪廓欄位）；
- current setting（目前設定）優先使用 host-injected evidence（宿主注入證據）；若缺少該證據，bounded `read_current_setting.py` fallback（有界後備讀取器）只能輸出 `current` 和 `current_provenance`，任何 `unknown` result（結果）都維持 recommendation-only（僅建議）；
- task continuation（任務繼續）需要 Codex Desktop（Codex 桌面端）、全部必要 task tool（任務工具）、已驗證的 current-setting evidence（目前設定證據）與 catalog evidence（模型目錄證據），以及宿主支援的推薦模型與 thinking；
- routing（路由）需要 `host_capabilities.source_task_context=true`，每次 transfer（轉移）還必須獨立取得有效的 `CODEX_THREAD_ID`；`transfer_state.py` 只在本機衍生 `source_binding_sha256`，不會持久儲存或輸出原始 source identifier（源任務識別碼）；
- 每一個 `fork -> send -> readback -> navigate -> archive` side effect（外部副作用）都需要自己的 atomic reservation（原子預留），且只有確認序列到達同一目標後，才允許 archive（封存）源任務。

## 快速開始

前置需求：

- 支援 Plugin（外掛程式）和明確 Skill invocation（技能呼叫）的 Codex surface（Codex 使用介面）；
- 可以從 `PATH` 執行 Codex CLI（Codex 命令列工具）；
- 可以存取公開 Git repository（Git 儲存庫）。

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

建立新的 Codex task（Codex 任務），選擇 **Auto Route for Codex**，或輸入：

```text
$auto-route-for-codex 檢查這項任務，並使用足以完成任務的 Codex 設定。
```

Plugin（外掛程式）始終傳回帶版本的 decision（決策），並優先使用 host-injected current setting（宿主注入的目前設定）。如果缺少該 observation（觀測），且 `CODEX_THREAD_ID` 與可用的 `CODEX_HOME` 都存在，`read_current_setting.py` 只能檢查 `$CODEX_HOME/sessions` 中符合的 local session（本機工作階段），並輸出不含 task text（任務正文）、path（路徑）或 thread identifier（任務識別碼）的 bounded `current + current_provenance` result（有界結果）。Reader failure（讀取失敗）會傳回 `unknown`。在能力完整的 Codex Desktop host（Codex 桌面端宿主）中，已驗證的 `quality` 或 `parallelism` mismatch（不匹配）可以在 fork（派生任務）中使用推薦的 `model` 和 `thinking` 繼續；`efficiency` mismatch（效率不匹配）、不支援的 surface（使用介面）、缺少工具、不支援的設定或 `unknown|stale|uncertain` evidence（證據）都保持 `stay` 與 recommendation-only（僅建議）。

Plugin（外掛程式）不會修改 native model picker（原生模型選擇器）、`config.toml`、persistent default（持久預設值）、sandbox（沙箱）、approval policy（審批政策）、network access（網路權限）或 credential（憑證）。

每次 transfer（轉移）都使用 source-task binding（源任務綁定）：routing-time host evidence（路由時宿主證據）必須宣告 `host_capabilities.source_task_context=true`，執行時還必須提供有效的 `CODEX_THREAD_ID`，兩者缺一不可。`transfer_state.py` 只在本機衍生 `source_binding_sha256`，不會持久儲存或輸出原始 source identifier（源任務識別碼）。此 hash（雜湊值）會進入 per-source lock key（依源任務鎖定鍵）、canonical receipt（規範回執）、`authorization_binding`、reservation marker（預留標記）以及包含 archive confirmation（封存確認）的每次狀態驗證。因此，同一源任務不能透過不同 `transfer_id` 再啟動一次轉移，錯誤源任務也不能恢復、確認或封存該轉移；源任務內容缺失、無效或不相符時會 fail closed（證據不足即停止）。

## 受 capability gate（能力門檻）保護的 Desktop continuation（桌面端任務繼續）

只有以下檢查全部通過，完整路徑才可使用：

1. 目前 surface（使用介面）是 Codex Desktop（Codex 桌面端）；
2. host（宿主）提供相容的 `fork_thread`、`send_message_to_thread`、`read_thread`、`navigate_to_codex_page` 和 `set_thread_archived` capability（能力）；
3. current-setting evidence（目前設定證據）為 `verified` 且仍有效，並優先使用 host injection（宿主注入），只在需要時使用 bounded fallback（有界後備讀取器）；model-catalog evidence（模型目錄證據）也必須為 `verified` 且仍有效；
4. 推薦的 `model` 和 `thinking` 受 live host（目前宿主）支援；
5. 每次呼叫 fork（派生）、send（傳送）、readback（回讀）、navigation（導覽）或 archive（封存）之前，`transfer_state.py --reserve-event` 都會在 durable default root（持久預設根目錄）`$CODEX_HOME/state/auto-route-for-codex` 建立 atomic `O_EXCL` marker（原子排他標記）；`AUTO_ROUTE_STATE_HOME` 只作為 explicit override/test hook（明確覆寫或測試掛鉤），且只有 `side_effect_authorized=true` 時，才會使用 reservation（預留）傳回的 winner-only `reservation_lease`（僅勝出者租約）執行 host call（宿主呼叫）；
6. prompt delivery（提示傳送）會確認實際使用的 model override（模型覆寫值）和 thinking override（思考檔位覆寫值），destination readback（目標任務回讀）證明去除呼叫詞後的原始任務已到達精確 fork（派生任務），而 navigation（導覽）必須在允許 archive（封存）之前成功。

固定 lifecycle（生命週期）為：

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

Successful reservation（成功預留）會傳回 winner-only `reservation_lease`（僅勝出者租約）；執行 host side effect（宿主外部副作用）後，以 `--event`、相同的 `--router-input`，並用 `--reservation-lease` 傳入該租約來確認。`prompt_delivery_confirmed` 還需要 `--observed-model` 與 `--observed-thinking`。Canonical receipt（規範回執）會持久保存 `pending_reservation`；因此即使 marker（標記）遺失，重複 reserve（預留）仍會傳回 `reconcile_required` 和 `side_effect_authorized=false`，絕不重新授權外部副作用。Marker（標記）、receipt（回執）與 newly created state directory（新建狀態目錄）都會執行 `fsync`。預設根目錄 `$CODEX_HOME/state/auto-route-for-codex` 本身可持久保存；`AUTO_ROUTE_STATE_HOME` 只作為 explicit override/test hook（明確覆寫或測試掛鉤），不是持久化的必要條件。Reservation marker（預留標記）只包含 hash（雜湊）與 bounded transfer metadata（有界轉移中繼資料），絕不保存 raw task text（原始任務正文），也絕不進入 package（套件）或 repository（儲存庫）。

`reservation_lease` 是 ephemeral coordination nonce（一次性協調隨機值）與 bearer capability（持有即可確認的能力），不是 credential（憑證）。它只會在勝出操作的 private local CLI stdout（私有本機命令列標準輸出）或同等 tool-execution detail（工具執行明細）中輸出一次，再透過 process argument（程序參數）`--reservation-lease` 回傳；未來相容介面也可改用 stdin（標準輸入）。它必須留在該私有操作內，不得複製到 task prompt（任務提示）、final 或其他 user-facing prose（使用者可見文字）、package（套件）、repository（儲存庫）、external telemetry（外部遙測）、Issue/support report（問題或支援報告）或 durable log（持久日誌）。這可減少意外洩露，但不能防禦 malicious same-user writer（同一使用者權限下的惡意寫入者）。

Expired/stale evidence（已過期證據）絕不能授權新的 reservation（預留）。如果 immutable binding（不可變綁定）有效時，reservation（預留）已持久記錄為 `pending_reservation`，即使後來超過 evidence TTL（證據有效期），匹配 lease（租約）仍只能確認這項已開始操作，或把它標記為 `uncertain`；不能據此授權新的 host side effect（宿主副作用）。唯一受支援的 state mutation interface（狀態修改介面）是 `transfer_state.py` CLI（命令列介面）。透過 Python import（Python 匯入）呼叫內部實作或直接修改 state file（狀態檔案）都屬於 unsupported internals（不受支援的內部用法）。

Timeout（逾時）、mismatch（不一致）、incomplete result（不完整結果）或 ambiguous side effect（不明確副作用）會進入 `uncertain`。不得 resend（重複傳送）、refork（再次派生）、在源任務中執行原始請求或封存源任務。已知 destination identifier（目標任務編號）時，只能對帳該目標任務。如果 fork（派生任務）實際成功，但 host response（宿主回應）在傳回任何 destination identifier（目標任務編號）前遺失，durable replay protection（持久重放保護）仍會阻止 refork（再次派生）、源任務執行和源任務封存，但 Plugin（外掛）無法自行發現未知目標任務。請保持源任務可見，並透過 host UI（宿主介面）或 support channel（支援管道）定位或復原目標任務。這能防止 duplicate execution（重複執行），但不能證明 zero lost tasks（零任務遺失）。Receipt hash（回執雜湊）與 reservation hash（預留雜湊）提供 deterministic integrity（確定性完整性），不是 signature（數位簽章）；能夠替換本機狀態的 malicious local writer（惡意本機寫入者）不在 threat boundary（威脅邊界）內。

## 公開版安全界線

包含：

- 嚴格的 JSON input/output/transfer-receipt schema（JSON 輸入、輸出與轉移回執結構規範）；
- deterministic routing（確定性路由）、bounded current-setting fallback（有界目前設定後備讀取）和 reservation-backed transfer-state logic（預留保護的轉移狀態邏輯）；
- privacy-preserving source-task binding（保護隱私的源任務綁定），它會阻止錯誤源任務恢復轉移，也會阻止同一源任務使用多個 `transfer_id`；
- 受 capability gate（能力門檻）保護的 Codex Desktop task continuation contract（桌面端任務繼續契約）；
- route/contract/semantic-negative/state-machine/failure-boundary test（路由、契約、語意負向、狀態機與失敗邊界測試）；
- repository/privacy/translation/Release verification（儲存庫、隱私、翻譯與發行驗證）；
- English authoritative documentation（英文權威文件）、完整 Simplified Chinese translation（簡體中文翻譯）和多語言 README entry point（說明入口）。

刻意排除：

- unbounded session scanning（無界工作階段掃描）、task-text extraction（任務正文擷取），或匯出 session content（工作階段內容）與 reservation marker（預留標記）；
- 私有 current-setting receipt（目前設定回執）、private catalog（私有目錄）或 local marketplace state（本機市集狀態）；
- runtime log（執行階段日誌）、credential（憑證）、本機 path（路徑）、task identifier（任務識別碼）或 private configuration（私有設定）；
- hidden invocation（隱藏呼叫）、針對 `efficiency` 的自動轉移、修改 native model picker（原生模型選擇器）或寫入 Codex global configuration（全域設定）；
- 宣稱 Codex CLI、IDE、cloud、API 或其他 Agent 提供 Codex Desktop task tool（桌面端任務工具）。

請參閱 [Privacy and data flow](docs/privacy-and-data-flow.md)、[Routing policy](docs/routing-policy.md) 和 [Compatibility](docs/compatibility.md)。

## 儲存庫結構

| Path | 用途 |
|---|---|
| `.codex-plugin/plugin.json` | Plugin manifest（外掛程式資訊清單） |
| `.agents/plugins/marketplace.json` | Marketplace entry（市集項目） |
| `skills/auto-route-for-codex/` | Skill（技能）、schema（結構規範）、bounded current-setting reader（有界目前設定讀取器）、Router（路由器）、reservation-backed transfer reducer（預留保護的轉移歸約器）和測試 |
| `docs/` | 權威 English（英文）文件 |
| `docs/i18n/zh-CN/` | 完整的 Simplified Chinese（簡體中文）翻譯 |
| `scripts/verify_public_repo.py` | Repository（儲存庫）、翻譯、隱私和連結檢查 |
| `scripts/build_release.py` | 確定性的 Plugin ZIP（外掛程式壓縮檔）和 `SHA256SUMS` 建置工具 |

## 從乾淨的 Clone 驗證

```sh
python3 -m pip install --disable-pip-version-check PyYAML==6.0.3 jsonschema==4.26.0
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

`v0.5.0-alpha.1` 是第一個提供 capability-gated Codex Desktop task continuation（受能力門檻保護的桌面端任務繼續）的公開 Alpha（早期測試）版本。在 stable release（穩定版本）推出之前，API 和 package layout（套件結構）可能會變更。請參閱 [CHANGELOG.md](CHANGELOG.md) 和 [ROADMAP.md](ROADMAP.md)。

## 貢獻與安全性

建立 pull request（提取要求）之前，請先閱讀 [CONTRIBUTING.md](CONTRIBUTING.md)。請依照 [SECURITY.md](SECURITY.md) 的說明，透過 GitHub private vulnerability reporting（GitHub 私密漏洞回報）提交安全問題；請勿在公開 issue（議題）中發布敏感報告。

## 授權條款

Apache License 2.0。請參閱 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。
