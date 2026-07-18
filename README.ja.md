---
translation_of: README.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# Auto Route for Codex

**言語：** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | 日本語 | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Alpha（アルファ）コミュニティプロジェクト。OpenAI の公式製品ではありません。

Auto Route for Codex は、明示的にオプトインして使用する Codex Plugin（Codex プラグイン）です。プライバシーの境界が定められた task profile（タスクプロファイル）に基づき、タスクの遂行に十分な model role（モデルロール）、reasoning effort（推論強度）、execution topology（実行トポロジー）を推奨します。公開版は意図的に recommendation-only（推奨のみ）とされており、タスクの fork（フォーク）、作成、移動、アーカイブ、再実行を行うことはありません。

## このプロジェクトが存在する理由

Model choice（モデル選択）と reasoning effort（推論強度）は別々の判断です。短くてもリスクの高いタスクには高性能な Model（モデル）が必要な場合があり、長時間にわたる反復的で検証可能な処理には、より高速な Model（モデル）が適している場合があります。この Plugin（プラグイン）は、モデル選択を見えない side effect（副作用）にすることなく、こうしたトレードオフを明示します。

公開 contract（契約）は、次の 4 つのルールに従います。

- `$auto-route-for-codex` によって明示的に有効化されること。
- deterministic router（決定論的ルーター）に渡されるのは、列挙済みの profile field（プロファイルフィールド）だけであること。
- recommendation（推奨）は、host（ホスト）が提供する Model（モデル）と thinking（思考レベル）の値だけに解決されること。
- すべての公開 decision（決定）が `stay + none|efficiency + none + keep` のままであること。

## クイックスタート

前提条件：

- Plugin（プラグイン）と明示的な Skill invocation（スキル呼び出し）をサポートする Codex surface（Codex 利用環境）。
- `PATH` から利用できる Codex CLI（Codex コマンドラインツール）。
- 公開 Git repository（Git リポジトリ）へのアクセス。

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

新しい Codex task（Codex タスク）を開始して **Auto Route for Codex** を選択するか、次のように呼び出します。

```text
$auto-route-for-codex このタスクを確認し、十分な Codex 設定を推奨してください。
```

Plugin（プラグイン）はバージョン付きの recommendation（推奨）を返します。現在のタスクの Model（モデル）や設定を変更することはありません。

## 公開版の安全境界

含まれるもの：

- 厳格な JSON input and output schemas（JSON 入出力スキーマ）。
- deterministic routing logic（決定論的ルーティングロジック）。
- recommendation-only tests（推奨のみのテスト）と semantic negative cases（意味論的な否定ケース）。
- 公開 repository（リポジトリ）と Release（リリース）の検証スクリプト。
- English（英語）ドキュメントと完全な Simplified Chinese（簡体字中国語）ドキュメント。

意図的に除外されるもの：

- ローカルの session-file reader（セッションファイル読み取り機能）。
- 非公開の current-setting receipt（現在設定の記録）または catalog（カタログ）。
- タスクの fork（フォーク）、移動、アーカイブ、再実行のオーケストレーション。
- runtime log（実行時ログ）、credential（認証情報）、ローカル path（パス）、task identifier（タスク識別子）、private configuration（非公開設定）。
- Model（モデル）の自動変更、または Codex global configuration（Codex グローバル設定）への書き込み。

[Privacy and data flow](docs/privacy-and-data-flow.md) と [Routing policy](docs/routing-policy.md) を参照してください。

## リポジトリ構成

| Path | 用途 |
|---|---|
| `.codex-plugin/plugin.json` | Plugin manifest（プラグインマニフェスト） |
| `.agents/plugins/marketplace.json` | Marketplace entry（マーケットプレイス項目） |
| `skills/auto-route-for-codex/` | Skill（スキル）、schema（スキーマ）、Router（ルーター）、テスト |
| `docs/` | 正式な English（英語）ドキュメント |
| `docs/i18n/zh-CN/` | 完全な Simplified Chinese（簡体字中国語）翻訳 |
| `scripts/verify_public_repo.py` | Repository（リポジトリ）、翻訳、プライバシー、リンクの検査 |
| `scripts/build_release.py` | 決定論的な Plugin ZIP（プラグイン ZIP）と `SHA256SUMS` のビルドツール |

## クリーンな Clone から検証する

```sh
python3 scripts/verify_public_repo.py
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

`v0.4.0-alpha.1` は最初の公開 Alpha（アルファ）版です。stable release（安定版）の公開前に、API と package layout（パッケージ構成）が変更される可能性があります。[CHANGELOG.md](CHANGELOG.md) と [ROADMAP.md](ROADMAP.md) を参照してください。

## コントリビューションとセキュリティ

pull request（プルリクエスト）を作成する前に [CONTRIBUTING.md](CONTRIBUTING.md) をお読みください。セキュリティ上の問題は [SECURITY.md](SECURITY.md) の説明に従い、GitHub private vulnerability reporting（GitHub の非公開脆弱性報告）から報告してください。機密性の高い報告を公開 issue（Issue）に投稿しないでください。

## ライセンス

Apache License 2.0。[LICENSE](LICENSE) と [NOTICE](NOTICE) を参照してください。
