---
translation_of: README.md
source_revision: docs-v0.5.0-alpha.2
last_synced_version: 0.5.0-alpha.2
---

# Auto Route for Codex

**언어:** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | 한국어 | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Alpha(알파) 커뮤니티 프로젝트입니다. OpenAI 공식 제품이 아닙니다.

Auto Route for Codex는 사용자가 명시적으로 선택하여 사용하는 Codex Plugin(Codex 플러그인)입니다. 개인정보 보호 범위가 제한된 task profile(작업 프로필)을 바탕으로 충분한 model role(모델 역할), reasoning effort(추론 강도), execution topology(실행 토폴로지)를 추천합니다. 지원되는 Codex Desktop host에서는 host capability와 evidence gate를 모두 통과한 경우에만 `quality` 또는 `parallelism`이 중요한 작업을 fork에서 계속할 수 있습니다. 다른 환경에서는 현재 작업의 recommendation으로 안전하게 전환됩니다.

## 이 프로젝트가 필요한 이유

Model choice(모델 선택)와 reasoning effort(추론 강도)는 서로 다른 결정입니다. 짧지만 위험한 작업에는 더 강력한 Model(모델)이 필요할 수 있고, 장시간 반복되며 검증 가능한 작업에는 더 빠른 Model(모델)이 적합할 수 있습니다. 이 Plugin(플러그인)은 모델 선택을 보이지 않는 side effect(부작용)로 만들지 않으면서 이러한 절충 관계를 명확하게 드러냅니다.

공개 contract(계약)는 다음 여섯 가지 규칙을 따릅니다.

- `$auto-route-for-codex`를 통해 명시적으로 활성화합니다.
- deterministic router(결정론적 라우터)에는 열거된 profile field(프로필 필드)만 전달합니다.
- current setting은 host-injected evidence를 우선하며, 이것이 없을 때 bounded `read_current_setting.py` fallback은 `current`와 `current_provenance`만 출력할 수 있고 모든 `unknown` 결과는 recommendation-only로 유지됩니다.
- task continuation에는 Codex Desktop, 모든 필수 task tool, 검증된 current-setting 및 catalog evidence, host가 지원하는 추천 model과 thinking이 필요합니다.
- routing에는 `host_capabilities.source_task_context=true`가 필요하고 각 전송에는 독립적으로 유효한 `CODEX_THREAD_ID`가 필요합니다. `transfer_state.py`는 로컬에서 `source_binding_sha256`을 파생하며 원본 식별자를 저장하거나 출력하지 않습니다.
- `fork -> send -> readback -> navigate -> archive`의 각 side effect에는 별도의 atomic reservation이 필요하며, 확인된 순서가 하나의 대상에 도달한 뒤에만 원본 작업을 archive할 수 있습니다.

## 빠른 시작

필수 조건:

- Plugin(플러그인)과 명시적인 Skill invocation(스킬 호출)을 지원하는 Codex surface(Codex 사용 환경).
- `PATH`에서 사용할 수 있는 Codex CLI(Codex 명령줄 도구).
- 공개 Git repository(Git 저장소)에 대한 접근 권한.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.2
codex plugin add auto-route-for-codex@jacob101519
```

새 Codex task(Codex 작업)를 시작하고 **Auto Route for Codex**를 선택하거나 다음과 같이 호출합니다.

```text
$auto-route-for-codex 이 작업을 검토하고 충분한 Codex 설정을 사용해 주세요.
```

Plugin은 항상 버전이 지정된 decision을 반환하고 host-injected current setting을 우선합니다. 해당 observation이 없고 `CODEX_THREAD_ID`와 사용 가능한 `CODEX_HOME`이 있으면 `read_current_setting.py`는 `$CODEX_HOME/sessions`에서 일치하는 local session만 검사하고 task text, path 또는 thread identifier가 없는 bounded `current + current_provenance` 결과를 출력할 수 있습니다. Reader failure는 `unknown`을 반환합니다. 지원되는 Codex Desktop host에서는 검증된 `quality` 또는 `parallelism` mismatch를 추천 `model`과 `thinking`을 사용한 fork에서 계속할 수 있지만, `efficiency` mismatch, 지원되지 않는 surface, 누락된 tool, 지원되지 않는 설정 또는 `unknown|stale|uncertain` evidence는 `stay` 및 recommendation-only로 유지됩니다.

Plugin은 native model picker, `config.toml`, 영구 기본값, sandbox, approval policy, network access 또는 credential을 변경하지 않습니다.

모든 전송은 원본 작업에 바인딩됩니다. 라우팅 시 호스트 증거는 `host_capabilities.source_task_context=true`를 선언해야 하며, 실행 시에도 유효한 `CODEX_THREAD_ID`가 필요합니다. 둘 다 필수입니다. `transfer_state.py`는 로컬에서 `source_binding_sha256`을 파생하며 원본 식별자 원문을 저장하거나 출력하지 않습니다. 이 해시는 원본별 잠금 키, 정규 영수증, `authorization_binding`, 각 예약 마커, 아카이브 확인을 포함한 모든 전이 검증에 들어갑니다. 따라서 같은 원본은 다른 `transfer_id`로 두 번째 전송을 시작할 수 없고 다른 원본은 전송을 재개, 확인 또는 아카이브할 수 없습니다. 원본 컨텍스트가 없거나 잘못되었거나 일치하지 않으면 fail closed합니다.

## Capability gate로 보호되는 Desktop 연속 실행

전체 경로는 다음 검사를 모두 통과한 경우에만 사용할 수 있습니다.

1. 현재 surface가 Codex Desktop입니다.
2. host가 호환되는 `fork_thread`, `send_message_to_thread`, `read_thread`, `navigate_to_codex_page`, `set_thread_archived` capability를 제공합니다.
3. current-setting evidence는 `verified`이고 유효하며 host injection을 우선하고 필요할 때만 bounded fallback을 사용하며, model-catalog evidence도 `verified`이고 유효합니다.
4. 추천 `model`과 `thinking`을 live host가 지원합니다.
5. fork, send, readback, navigation 또는 archive 호출 전에 `transfer_state.py --reserve-event`가 durable default root인 `$CODEX_HOME/state/auto-route-for-codex`에 atomic `O_EXCL` marker를 만듭니다. `AUTO_ROUTE_STATE_HOME`은 explicit override/test hook일 뿐이며, host call은 `side_effect_authorized=true`일 때 reservation이 반환한 winner-only `reservation_lease`를 사용해서만 실행됩니다.
6. prompt delivery는 실제 model 및 thinking override를 확인하고, destination readback은 호출어를 제거한 원래 요청이 정확한 fork에 도착했음을 증명하며, archive가 승인되기 전에 navigation이 성공합니다.

순서가 정해진 lifecycle은 다음과 같습니다.

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

Successful reservation은 winner-only `reservation_lease`를 반환합니다. Host side effect 뒤에는 같은 `--router-input`과 `--event`를 사용하고 해당 lease를 `--reservation-lease`로 전달해 확인합니다. `prompt_delivery_confirmed`에는 `--observed-model`과 `--observed-thinking`도 필요합니다. Canonical receipt는 `pending_reservation`을 영구 저장하므로 marker가 없어져도 반복 reserve는 `reconcile_required`와 `side_effect_authorized=false`를 반환하고 side effect를 다시 승인하지 않습니다. Marker, receipt 및 새로 만든 state directory는 모두 `fsync`됩니다. 기본 root `$CODEX_HOME/state/auto-route-for-codex` 자체가 durable하며 `AUTO_ROUTE_STATE_HOME`은 explicit override/test hook일 뿐 persistence에 필요하지 않습니다. Reservation marker에는 hash와 bounded transfer metadata만 포함되고 raw task text는 저장하지 않으며 package나 repository에 들어가지 않습니다.

`reservation_lease`는 ephemeral coordination nonce이자 bearer capability이며 credential이 아닙니다. 승리한 작업의 private local CLI stdout 또는 이에 해당하는 tool-execution detail에 한 번만 출력되고 process argument `--reservation-lease`로 다시 전달됩니다. 향후 호환 인터페이스는 stdin을 사용할 수 있습니다. 이 값은 해당 비공개 작업 안에만 두고 task prompt, final 또는 기타 user-facing prose, package나 repository, external telemetry, Issue나 support report, durable log에 복사하지 마십시오. 이 경계는 우발적 노출을 줄이지만 malicious same-user writer로부터 lease를 보호하지는 않습니다.

만료되었거나 stale인 evidence는 새 reservation을 절대 승인하지 않습니다. Immutable binding이 유효할 때 reservation이 이미 `pending_reservation`으로 영구 기록되었다면, 일치하는 lease는 evidence TTL이 지난 뒤에도 그 시작된 작업만 확인하거나 `uncertain`으로 표시할 수 있습니다. 이 예외로 다른 host side effect를 승인할 수 없습니다. 지원되는 state mutation interface는 `transfer_state.py` CLI뿐입니다. 구현을 Python import로 호출하거나 state file을 직접 변경하는 것은 unsupported internals입니다.

timeout, mismatch, 불완전한 결과 또는 모호한 side effect는 `uncertain`으로 전환됩니다. Plugin은 재전송, 재 fork, 원본에서 요청 실행 또는 원본 archive를 하면 안 됩니다. destination identifier를 알고 있으면 해당 대상만 조정할 수 있습니다. fork가 실제로 성공했지만 destination identifier가 반환되기 전에 host response가 유실된 경우에도 durable replay protection은 재 fork, 원본 실행 및 원본 archive를 계속 차단하지만, Plugin 자체는 알 수 없는 대상을 발견할 수 없습니다. 원본을 보이게 유지하고 host UI 또는 support channel을 사용해 대상을 찾거나 복구하십시오. 이는 duplicate execution을 방지하지만 lost task가 0임을 증명하지는 않습니다. Receipt 및 reservation hash는 deterministic integrity를 제공할 뿐 signature가 아니며, local state를 바꿀 수 있는 malicious local writer는 threat boundary 밖에 있습니다.

## 공개 버전의 안전 경계

포함되는 항목:

- 엄격한 JSON input/output/transfer-receipt schemas.
- deterministic routing, bounded current-setting fallback 및 reservation-backed transfer-state logic.
- 다른 원본에서의 재개와 하나의 원본에 대한 복수 `transfer_id`를 방지하는 privacy-preserving source-task binding.
- capability-gated Codex Desktop task continuation contract.
- route, contract, semantic-negative, state-machine, failure-boundary tests.
- 공개 repository, privacy, translation, Release verification.
- 기준 English 문서, 완전한 Simplified Chinese 번역 및 현지화된 README 진입점.

의도적으로 제외되는 항목:

- unbounded session scanning, task-text extraction 또는 session content 및 reservation marker 내보내기.
- 비공개 current-setting receipt, private catalog 또는 local marketplace state.
- runtime log(런타임 로그), credential(자격 증명), 로컬 path(경로), task identifier(작업 식별자), private configuration(비공개 설정).
- hidden invocation, `efficiency` 자동 전송, native model picker 변경 또는 Codex global configuration 쓰기.
- Codex CLI, IDE, cloud, API 또는 다른 Agent가 Codex Desktop task tool을 제공한다는 주장.

[Privacy and data flow](docs/privacy-and-data-flow.md), [Routing policy](docs/routing-policy.md), [Compatibility](docs/compatibility.md)를 참조하세요.

## 저장소 구성

| Path | 용도 |
|---|---|
| `.codex-plugin/plugin.json` | Plugin manifest(플러그인 매니페스트) |
| `.agents/plugins/marketplace.json` | Marketplace entry(마켓플레이스 항목) |
| `skills/auto-route-for-codex/` | Skill, schema, bounded current-setting reader, Router, reservation-backed transfer reducer 및 테스트 |
| `docs/` | 기준이 되는 English(영어) 문서 |
| `docs/i18n/zh-CN/` | 완전한 Simplified Chinese(중국어 간체) 번역 |
| `scripts/verify_public_repo.py` | Repository(저장소), 번역, 개인정보 보호, 링크 검사 |
| `scripts/build_release.py` | 결정론적 Plugin ZIP(플러그인 ZIP)과 `SHA256SUMS` 빌드 도구 |

## 깨끗한 Clone에서 검증하기

```sh
python3 -m pip install --disable-pip-version-check --only-binary=:all: --require-hashes -r .github/requirements-ci.txt
python3 scripts/verify_public_repo.py --require-git-history
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

`v0.5.0-alpha.2`는 공개 기록의 개인정보 보호, CI 종속성 무결성, 릴리스 출처 증명을 강화합니다. 런타임 라우팅 계약은 변경되지 않았습니다. [CHANGELOG.md](CHANGELOG.md)와 [ROADMAP.md](ROADMAP.md)를 참조하세요.

## 기여 및 보안

pull request(풀 리퀘스트)를 열기 전에 [CONTRIBUTING.md](CONTRIBUTING.md)를 읽어 주세요. 보안 문제는 [SECURITY.md](SECURITY.md)의 안내에 따라 GitHub private vulnerability reporting(GitHub 비공개 취약점 보고)을 통해 신고하세요. 민감한 보고서를 공개 issue(이슈)에 게시하지 마세요.

## 라이선스

Apache License 2.0. [LICENSE](LICENSE)와 [NOTICE](NOTICE)를 참조하세요.
