---
translation_of: README.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# Auto Route for Codex

**언어:** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | 한국어 | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Alpha(알파) 커뮤니티 프로젝트입니다. OpenAI 공식 제품이 아닙니다.

Auto Route for Codex는 사용자가 명시적으로 선택하여 사용하는 Codex Plugin(Codex 플러그인)입니다. 개인정보 보호 범위가 제한된 task profile(작업 프로필)을 바탕으로 작업에 충분한 model role(모델 역할), reasoning effort(추론 강도), execution topology(실행 토폴로지)를 추천합니다. 공개 버전은 의도적으로 recommendation-only(추천 전용)이며, 작업을 fork(분기), 생성, 이동, 보관하거나 다시 실행하지 않습니다.

## 이 프로젝트가 필요한 이유

Model choice(모델 선택)와 reasoning effort(추론 강도)는 서로 다른 결정입니다. 짧지만 위험한 작업에는 더 강력한 Model(모델)이 필요할 수 있고, 장시간 반복되며 검증 가능한 작업에는 더 빠른 Model(모델)이 적합할 수 있습니다. 이 Plugin(플러그인)은 모델 선택을 보이지 않는 side effect(부작용)로 만들지 않으면서 이러한 절충 관계를 명확하게 드러냅니다.

공개 contract(계약)는 다음 네 가지 규칙을 따릅니다.

- `$auto-route-for-codex`를 통해 명시적으로 활성화합니다.
- deterministic router(결정론적 라우터)에는 열거된 profile field(프로필 필드)만 전달합니다.
- recommendation(추천)은 host(호스트)가 제공한 Model(모델) 및 thinking(사고 단계) 값에 대해서만 결정됩니다.
- 모든 공개 decision(결정)은 `stay + none|efficiency + none + keep`으로 유지됩니다.

## 빠른 시작

필수 조건:

- Plugin(플러그인)과 명시적인 Skill invocation(스킬 호출)을 지원하는 Codex surface(Codex 사용 환경).
- `PATH`에서 사용할 수 있는 Codex CLI(Codex 명령줄 도구).
- 공개 Git repository(Git 저장소)에 대한 접근 권한.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

새 Codex task(Codex 작업)를 시작하고 **Auto Route for Codex**를 선택하거나 다음과 같이 호출합니다.

```text
$auto-route-for-codex 이 작업을 검토하고 충분한 Codex 설정을 추천해 주세요.
```

Plugin(플러그인)은 버전이 지정된 recommendation(추천)을 반환합니다. 현재 작업의 Model(모델)이나 설정은 변경하지 않습니다.

## 공개 버전의 안전 경계

포함되는 항목:

- 엄격한 JSON input and output schemas(JSON 입력 및 출력 스키마).
- deterministic routing logic(결정론적 라우팅 로직).
- recommendation-only tests(추천 전용 테스트)와 semantic negative cases(의미론적 부정 사례).
- 공개 repository(저장소)와 Release(릴리스) 검증 스크립트.
- English(영어) 문서와 완전한 Simplified Chinese(중국어 간체) 문서.

의도적으로 제외되는 항목:

- 로컬 session-file reader(세션 파일 판독기).
- 비공개 current-setting receipt(현재 설정 확인 기록) 또는 catalog(카탈로그).
- 작업 fork(분기), 이동, 보관 및 재실행 오케스트레이션.
- runtime log(런타임 로그), credential(자격 증명), 로컬 path(경로), task identifier(작업 식별자), private configuration(비공개 설정).
- Model(모델) 자동 변경 또는 Codex global configuration(Codex 전역 설정) 쓰기.

[Privacy and data flow](docs/privacy-and-data-flow.md)와 [Routing policy](docs/routing-policy.md)를 참조하세요.

## 저장소 구성

| Path | 용도 |
|---|---|
| `.codex-plugin/plugin.json` | Plugin manifest(플러그인 매니페스트) |
| `.agents/plugins/marketplace.json` | Marketplace entry(마켓플레이스 항목) |
| `skills/auto-route-for-codex/` | Skill(스킬), schema(스키마), Router(라우터), 테스트 |
| `docs/` | 기준이 되는 English(영어) 문서 |
| `docs/i18n/zh-CN/` | 완전한 Simplified Chinese(중국어 간체) 번역 |
| `scripts/verify_public_repo.py` | Repository(저장소), 번역, 개인정보 보호, 링크 검사 |
| `scripts/build_release.py` | 결정론적 Plugin ZIP(플러그인 ZIP)과 `SHA256SUMS` 빌드 도구 |

## 깨끗한 Clone에서 검증하기

```sh
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

로컬 검사를 통과하면 repository contract(저장소 계약)가 유효함을 확인할 수 있습니다. 하지만 모든 Codex host version(Codex 호스트 버전)이 동일한 Plugin(플러그인) 또는 Model surface(모델 인터페이스)를 제공한다는 의미는 아닙니다. [Compatibility](docs/compatibility.md)를 참조하세요.

## 문서

- [Architecture](docs/architecture.md)
- [Installation and rollback](docs/installation.md)
- [Configuration contract](docs/configuration.md)
- [Privacy and data flow](docs/privacy-and-data-flow.md)
- [Routing policy](docs/routing-policy.md)
- [Compatibility](docs/compatibility.md)
- [Troubleshooting](docs/troubleshooting.md)
- [FAQ](docs/faq.md)

## 프로젝트 상태

`v0.4.0-alpha.1`은 첫 번째 공개 Alpha(알파) 버전입니다. stable release(안정 버전) 이전에는 API와 package layout(패키지 구성)이 변경될 수 있습니다. [CHANGELOG.md](CHANGELOG.md)와 [ROADMAP.md](ROADMAP.md)를 참조하세요.

## 기여 및 보안

pull request(풀 리퀘스트)를 열기 전에 [CONTRIBUTING.md](CONTRIBUTING.md)를 읽어 주세요. 보안 문제는 [SECURITY.md](SECURITY.md)의 안내에 따라 GitHub private vulnerability reporting(GitHub 비공개 취약점 보고)을 통해 신고하세요. 민감한 보고서를 공개 issue(이슈)에 게시하지 마세요.

## 라이선스

Apache License 2.0. [LICENSE](LICENSE)와 [NOTICE](NOTICE)를 참조하세요.
