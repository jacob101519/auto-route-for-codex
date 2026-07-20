---
translation_of: README.md
source_revision: docs-v0.5.0-alpha.2
last_synced_version: 0.5.0-alpha.2
---

# Auto Route for Codex

**言語：** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | 日本語 | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Alpha（アルファ）コミュニティプロジェクト。OpenAI の公式製品ではありません。

Auto Route for Codex は、明示的にオプトインして使用する Codex Plugin（Codex プラグイン）です。プライバシーの境界が定められた task profile（タスクプロファイル）に基づき、十分な model role（モデルロール）、reasoning effort（推論強度）、execution topology（実行トポロジー）を推奨します。対応する Codex Desktop host（Codex Desktop ホスト）では、host capability（ホスト機能）と evidence gate（証拠ゲート）を通過した場合に限り、`quality` または `parallelism` が重要なタスクを fork（フォーク）で継続できます。それ以外の環境では現在のタスク内の recommendation（推奨）へ安全にフォールバックします。

## このプロジェクトが存在する理由

Model choice（モデル選択）と reasoning effort（推論強度）は別々の判断です。短くてもリスクの高いタスクには高性能な Model（モデル）が必要な場合があり、長時間にわたる反復的で検証可能な処理には、より高速な Model（モデル）が適している場合があります。この Plugin（プラグイン）は、モデル選択を見えない side effect（副作用）にすることなく、こうしたトレードオフを明示します。

公開 contract（契約）は、次の 6 つのルールに従います。

- `$auto-route-for-codex` によって明示的に有効化されること。
- deterministic router（決定論的ルーター）に渡されるのは、列挙済みの profile field（プロファイルフィールド）だけであること。
- current setting（現在設定）は host-injected evidence（ホスト注入証拠）を優先し、それがない場合の bounded `read_current_setting.py` fallback（有界フォールバック）は `current` と `current_provenance` だけを出力でき、`unknown` の結果はすべて recommendation-only（推奨のみ）になること。
- task continuation（タスク継続）には Codex Desktop、必要な task tool（タスクツール）、検証済みの current-setting evidence（現在設定の証拠）と catalog evidence（カタログ証拠）、およびホスト対応の推奨モデルと thinking が必要であること。
- routing（ルーティング）には `host_capabilities.source_task_context=true` が必要で、それとは独立して各転送に有効な `CODEX_THREAD_ID` が必要であること。`transfer_state.py` はローカルで `source_binding_sha256` を導出し、生のソース識別子を永続化も出力もしないこと。
- `fork -> send -> readback -> navigate -> archive` の各 side effect（副作用）には個別の atomic reservation（アトミック予約）が必要であり、確認済みのシーケンスが 1 つの宛先に到達した後にのみ元タスクを archive（アーカイブ）できること。

## クイックスタート

前提条件：

- Plugin（プラグイン）と明示的な Skill invocation（スキル呼び出し）をサポートする Codex surface（Codex 利用環境）。
- `PATH` から利用できる Codex CLI（Codex コマンドラインツール）。
- 公開 Git repository（Git リポジトリ）へのアクセス。

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.2
codex plugin add auto-route-for-codex@jacob101519
```

新しい Codex task（Codex タスク）を開始して **Auto Route for Codex** を選択するか、次のように呼び出します。

```text
$auto-route-for-codex このタスクを確認し、十分な Codex 設定を使用してください。
```

Plugin（プラグイン）は常にバージョン付き decision（決定）を返し、host-injected current setting（ホスト注入の現在設定）を優先します。その observation（観測）がなく、`CODEX_THREAD_ID` と利用可能な `CODEX_HOME` がある場合、`read_current_setting.py` は `$CODEX_HOME/sessions` 内の一致する local session（ローカルセッション）だけを調べ、task text（タスク本文）、path（パス）、thread identifier（スレッド識別子）を含まない bounded `current + current_provenance` result（有界結果）を出力できます。Reader failure（読み取り失敗）は `unknown` を返します。対応する Codex Desktop host（Codex Desktop ホスト）では、検証済みの `quality` または `parallelism` mismatch（不一致）を、推奨 `model` と `thinking` を指定した fork（フォーク）で継続できますが、`efficiency` mismatch（効率不一致）、未対応 surface（利用環境）、不足ツール、未対応設定、または `unknown|stale|uncertain` evidence（証拠）は `stay` と recommendation-only（推奨のみ）のままです。

Plugin（プラグイン）は native model picker（ネイティブモデル選択）、`config.toml`、永続的な既定値、sandbox（サンドボックス）、approval policy（承認方針）、network access（ネットワークアクセス）、credential（認証情報）を変更しません。

すべての転送はソースタスクに結び付けられます。ルーティング時のホスト証拠は `host_capabilities.source_task_context=true` を宣言し、実行時には有効な `CODEX_THREAD_ID` も必要です。どちらも省略できません。`transfer_state.py` はローカルで `source_binding_sha256` を導出し、生のソース識別子を永続化も出力もしません。このハッシュはソース単位のロックキー、正規レシート、`authorization_binding`、各予約マーカー、およびアーカイブ確認を含む全遷移検証に含まれます。同じソースは別の `transfer_id` で二重転送を開始できず、異なるソースは転送を再開、確認、アーカイブできません。ソースコンテキストが欠落、不正、または不一致なら fail closed になります。

## Capability gate で保護された Desktop 継続

完全な経路は、次の確認をすべて通過した場合のみ利用できます。

1. 現在の surface（利用環境）が Codex Desktop であること。
2. host（ホスト）が互換性のある `fork_thread`、`send_message_to_thread`、`read_thread`、`navigate_to_codex_page`、`set_thread_archived` capability（機能）を公開していること。
3. current-setting evidence（現在設定の証拠）が `verified` かつ有効で、host injection（ホスト注入）を優先し必要な場合だけ bounded fallback（有界フォールバック）を使い、model-catalog evidence（モデルカタログの証拠）も `verified` かつ有効であること。
4. 推奨 `model` と `thinking` が live host（現在のホスト）で対応していること。
5. fork、send、readback、navigation、archive の各呼出し前に、`transfer_state.py --reserve-event` が durable default root（永続的な既定ルート）`$CODEX_HOME/state/auto-route-for-codex` に atomic `O_EXCL` marker（アトミック排他マーカー）を作成すること。`AUTO_ROUTE_STATE_HOME` は explicit override/test hook（明示的な上書き・テスト用フック）に限り、`side_effect_authorized=true` の場合にだけ予約が返した winner-only `reservation_lease`（勝者専用リース）を使って host call（ホスト呼出し）を実行すること。
6. prompt delivery（プロンプト配信）が実際の model override（モデル上書き値）と thinking override（思考レベル上書き値）を確認し、destination readback（宛先の再読込）が呼出し語を除いた元の依頼が正確な fork に届いたことを証明し、archive（アーカイブ）の許可前に navigation（移動）が成功すること。

順序付き lifecycle（ライフサイクル）は次のとおりです。

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

Successful reservation（成功した予約）は winner-only `reservation_lease`（勝者専用リース）を返します。Host side effect（ホスト副作用）の後、同じ `--router-input` と `--event` を使い、そのリースを `--reservation-lease` で渡して確認します。`prompt_delivery_confirmed` では、さらに `--observed-model` と `--observed-thinking` が必要です。Canonical receipt（正規受領記録）は `pending_reservation` を永続化するため、marker（マーカー）が失われても再度の reserve（予約）は `reconcile_required` と `side_effect_authorized=false` を返し、副作用を再承認しません。Marker（マーカー）、receipt（受領記録）、新しく作成した state directory（状態ディレクトリ）はすべて `fsync` されます。既定ルート `$CODEX_HOME/state/auto-route-for-codex` は永続的であり、`AUTO_ROUTE_STATE_HOME` は explicit override/test hook（明示的な上書き・テスト用フック）にすぎず、永続化には不要です。Reservation marker（予約マーカー）は hash（ハッシュ）と bounded transfer metadata（有界転送メタデータ）だけを含み、raw task text（未加工のタスク本文）は保存せず、package（パッケージ）や repository（リポジトリ）には入りません。

`reservation_lease` は ephemeral coordination nonce（一時的な調整用ランダム値）かつ bearer capability（保持者が確認権限を持つ能力）であり、credential（認証情報）ではありません。勝者の private local CLI stdout（非公開ローカル CLI 標準出力）または同等の tool-execution detail（ツール実行詳細）に一度だけ出力され、process argument（プロセス引数）`--reservation-lease` で戻されます。将来の互換インターフェースでは stdin（標準入力）を使う場合があります。この値はその非公開操作内に限定し、task prompt（タスクプロンプト）、final などの user-facing prose（ユーザー向け文章）、package（パッケージ）、repository（リポジトリ）、external telemetry（外部テレメトリー）、Issue/support report（Issue またはサポート報告）、durable log（永続ログ）へコピーしてはいけません。この境界は偶発的な漏えいを減らしますが、malicious same-user writer（同一ユーザー権限の悪意ある書込み者）から lease を保護するものではありません。

期限切れまたは stale evidence（古い証拠）は、新しい reservation（予約）を決して承認しません。Immutable binding（不変バインディング）が有効な間に reservation が `pending_reservation` として永続記録済みなら、証拠の TTL が切れた後でも、一致する lease はその開始済み操作だけを確認するか `uncertain` にできます。この例外で別の host side effect（ホスト副作用）を承認することはできません。サポートされる state mutation interface（状態変更インターフェース）は `transfer_state.py` CLI だけです。実装の Python import（Python インポート）と state file（状態ファイル）の直接変更は unsupported internals（非サポートの内部利用）です。

timeout（タイムアウト）、不一致、不完全な結果、または曖昧な side effect（副作用）は `uncertain` になります。再送、再 fork、元タスクでの依頼実行、元タスクの archive は禁止されます。destination identifier（宛先識別子）が既知なら、その宛先だけを照合できます。実際には fork が成功していたものの、destination identifier が返る前に host response（ホスト応答）が失われた場合も、durable replay protection（永続的な再実行防止）は再 fork、元タスクでの実行、元タスクの archive を防ぎ続けますが、Plugin（プラグイン）自身は未知の宛先を発見できません。元タスクを表示したままにし、host UI（ホスト画面）または support channel（サポート窓口）を使って宛先を特定または復旧してください。これは duplicate execution（重複実行）を防ぎますが、lost task（失われるタスク）がゼロであることを証明しません。Receipt hash（受領記録ハッシュ）と reservation hash（予約ハッシュ）が提供するのは deterministic integrity（決定論的整合性）であり、signature（署名）ではありません。ローカル状態を置き換えられる malicious local writer（悪意あるローカル書込み者）は threat boundary（脅威境界）の対象外です。

## 公開版の安全境界

含まれるもの：

- 厳格な JSON input/output/transfer-receipt schemas（JSON 入出力・転送記録スキーマ）。
- deterministic routing（決定論的ルーティング）、bounded current-setting fallback（有界現在設定フォールバック）、reservation-backed transfer-state logic（予約で保護された転送状態ロジック）。
- 異なるソースからの再開と、1 つのソースに対する複数の `transfer_id` を防ぐ privacy-preserving source-task binding（プライバシー保護型ソースタスクバインディング）。
- capability gate で保護された Codex Desktop task continuation contract（タスク継続契約）。
- route、contract、semantic-negative、state-machine、failure-boundary tests（各種境界テスト）。
- 公開 repository、privacy、translation、Release verification（検証）。
- 正式な English（英語）ドキュメント、完全な Simplified Chinese（簡体字中国語）翻訳、ローカライズ済み README 入口。

意図的に除外されるもの：

- unbounded session scanning（無制限セッション走査）、task-text extraction（タスク本文抽出）、または session content（セッション内容）と reservation marker（予約マーカー）のエクスポート。
- 非公開の current-setting receipt（現在設定の記録）、private catalog（非公開カタログ）、local marketplace state（ローカル状態）。
- runtime log（実行時ログ）、credential（認証情報）、ローカル path（パス）、task identifier（タスク識別子）、private configuration（非公開設定）。
- hidden invocation（非表示呼出し）、`efficiency` の自動転送、native model picker の変更、Codex global configuration（グローバル設定）への書き込み。
- Codex CLI、IDE、cloud、API、他の Agent が Codex Desktop task tool を公開するという主張。

[Privacy and data flow](docs/privacy-and-data-flow.md)、[Routing policy](docs/routing-policy.md)、[Compatibility](docs/compatibility.md) を参照してください。

## リポジトリ構成

| Path | 用途 |
|---|---|
| `.codex-plugin/plugin.json` | Plugin manifest（プラグインマニフェスト） |
| `.agents/plugins/marketplace.json` | Marketplace entry（マーケットプレイス項目） |
| `skills/auto-route-for-codex/` | Skill（スキル）、schema（スキーマ）、bounded current-setting reader（有界現在設定リーダー）、Router（ルーター）、reservation-backed transfer reducer（予約で保護された転送リデューサー）、テスト |
| `docs/` | 正式な English（英語）ドキュメント |
| `docs/i18n/zh-CN/` | 完全な Simplified Chinese（簡体字中国語）翻訳 |
| `scripts/verify_public_repo.py` | Repository（リポジトリ）、翻訳、プライバシー、リンクの検査 |
| `scripts/build_release.py` | 決定論的な Plugin ZIP（プラグイン ZIP）と `SHA256SUMS` のビルドツール |

## クリーンな Clone から検証する

```sh
python3 -m pip install --disable-pip-version-check --only-binary=:all: --require-hashes -r .github/requirements-ci.txt
python3 scripts/verify_public_repo.py --require-git-history
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

ローカルチェックの成功は repository contract（リポジトリ契約）が有効であることを検証します。ただし、すべての Codex host version（Codex ホストバージョン）が同じ Plugin（プラグイン）や Model surface（モデルインターフェース）を公開していることを証明するものではありません。[Compatibility](docs/compatibility.md) を参照してください。

## ドキュメント

- [Architecture](docs/architecture.md)
- [Installation and rollback](docs/installation.md)
- [Configuration contract](docs/configuration.md)
- [Privacy and data flow](docs/privacy-and-data-flow.md)
- [Routing policy](docs/routing-policy.md)
- [Compatibility](docs/compatibility.md)
- [Troubleshooting](docs/troubleshooting.md)
- [FAQ](docs/faq.md)

## プロジェクトの状況

`v0.5.0-alpha.2` は公開履歴のプライバシー、CI 依存関係の完全性、リリース来歴を強化します。ランタイムのルーティング契約は変更されていません。[CHANGELOG.md](CHANGELOG.md) と [ROADMAP.md](ROADMAP.md) を参照してください。

## コントリビューションとセキュリティ

pull request（プルリクエスト）を作成する前に [CONTRIBUTING.md](CONTRIBUTING.md) をお読みください。セキュリティ上の問題は [SECURITY.md](SECURITY.md) の説明に従い、GitHub private vulnerability reporting（GitHub の非公開脆弱性報告）から報告してください。機密性の高い報告を公開 issue（Issue）に投稿しないでください。

## ライセンス

Apache License 2.0。[LICENSE](LICENSE) と [NOTICE](NOTICE) を参照してください。
