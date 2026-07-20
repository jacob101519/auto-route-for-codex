---
translation_of: README.md
source_revision: docs-v0.5.0-alpha.2
last_synced_version: 0.5.0-alpha.2
---

# Auto Route for Codex

**Язык:** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | Русский | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Альфа-версия проекта сообщества. Не является официальным продуктом OpenAI.

Auto Route for Codex — это плагин Codex с явным подключением, который на основе ограниченного с точки зрения конфиденциальности профиля задачи рекомендует достаточную роль модели, глубину рассуждений и топологию выполнения. На совместимом хосте Codex Desktop он может продолжить чувствительную к `quality` или `parallelism` задачу в fork только после проверки возможностей хоста и доказательств. Любая другая среда безопасно возвращается к рекомендации в текущей задаче.

## Зачем нужен этот проект

Выбор модели и глубины рассуждений — это разные решения. Для короткой, но рискованной задачи может потребоваться более мощная модель, тогда как для длительной, повторяющейся и проверяемой работы лучше подойдёт более быстрая модель. Этот плагин делает такие компромиссы явными, не превращая выбор модели в скрытый побочный эффект.

Публичный контракт следует шести правилам:

- активация выполняется явно через `$auto-route-for-codex`;
- в детерминированный маршрутизатор передаются только перечисленные поля профиля;
- текущая настройка отдаёт приоритет host-injected evidence; если таких данных нет, ограниченный fallback `read_current_setting.py` может вывести только `current` и `current_provenance`, а любой результат `unknown` остаётся recommendation-only;
- продолжение требует Codex Desktop, всех необходимых инструментов задач, проверенных данных текущей настройки и каталога, а также поддерживаемых хостом рекомендуемых модели и thinking;
- маршрутизация требует `host_capabilities.source_task_context=true`, а каждый перенос независимо требует действительный `CODEX_THREAD_ID`; `transfer_state.py` локально вычисляет `source_binding_sha256` и никогда не сохраняет и не выводит исходный идентификатор;
- каждый side effect в `fork -> send -> readback -> navigate -> archive` требует отдельного atomic reservation, а источник можно архивировать только после того, как подтверждённая последовательность достигнет одного назначения.

## Быстрый старт

Предварительные требования:

- интерфейс Codex, поддерживающий плагины и явный вызов навыков;
- Codex CLI, доступный через `PATH`;
- доступ к публичному Git-репозиторию.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.2
codex plugin add auto-route-for-codex@jacob101519
```

Запустите новую задачу Codex, выберите **Auto Route for Codex** или вызовите:

```text
$auto-route-for-codex Review this task and use a sufficient Codex setting.
```

Плагин всегда возвращает версионированное решение и отдаёт приоритет host-injected current setting. Если такого observation нет, но доступны `CODEX_THREAD_ID` и пригодный `CODEX_HOME`, `read_current_setting.py` может проверить только соответствующую local session в `$CODEX_HOME/sessions` и вывести ограниченный результат `current + current_provenance` без task text, path или thread identifier. Reader failure возвращает `unknown`. На совместимом хосте Codex Desktop проверенное расхождение `quality` или `parallelism` может продолжиться в fork с рекомендуемыми `model` и `thinking`; расхождение `efficiency`, неподдерживаемая среда, отсутствующий инструмент, неподдерживаемая настройка или данные `unknown|stale|uncertain` остаются `stay` и recommendation-only.

Плагин не меняет встроенный выбор модели, `config.toml`, постоянные значения, sandbox, политику подтверждений, доступ к сети или учётные данные.

Каждый перенос привязывается к исходной задаче: свидетельства хоста на этапе маршрутизации должны содержать `host_capabilities.source_task_context=true`, а во время выполнения также требуется действительный `CODEX_THREAD_ID`; необходимы оба условия. `transfer_state.py` локально вычисляет `source_binding_sha256` и никогда не сохраняет и не выводит исходный идентификатор источника. Хеш входит в ключ блокировки для источника, каноническую квитанцию, `authorization_binding`, каждый маркер резервирования и проверку каждого перехода, включая подтверждение архивирования. Поэтому один источник не может начать второй перенос с другим `transfer_id`, а другой источник не может возобновить, подтвердить или архивировать этот перенос. Отсутствующий, недействительный или несовпадающий контекст источника приводит к fail closed.

## Продолжение Desktop с проверкой возможностей

Полный путь доступен только после всех следующих проверок:

1. текущая среда — Codex Desktop;
2. хост предоставляет совместимые `fork_thread`, `send_message_to_thread`, `read_thread`, `navigate_to_codex_page` и `set_thread_archived`;
3. данные текущей настройки имеют состояние `verified` и актуальны, сначала используется host injection и только при необходимости bounded fallback; данные каталога моделей также имеют состояние `verified` и актуальны;
4. активный хост поддерживает рекомендуемые `model` и `thinking`;
5. перед каждым вызовом fork, send, readback, navigation или archive команда `transfer_state.py --reserve-event` создаёт atomic marker `O_EXCL` в durable default root `$CODEX_HOME/state/auto-route-for-codex`. `AUTO_ROUTE_STATE_HOME` служит только explicit override/test hook, а вызов хоста выполняется при `side_effect_authorized=true` только с winner-only `reservation_lease`, возвращённым reservation;
6. prompt delivery подтверждает фактические значения model и thinking override, чтение назначения доказывает, что очищенный исходный запрос попал в точный fork, а navigation завершается до разрешения archive.

Упорядоченный жизненный цикл:

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

Successful reservation возвращает winner-only `reservation_lease`. После host side effect подтверждение через `--event` использует тот же `--router-input` и передаёт lease как `--reservation-lease`; для `prompt_delivery_confirmed` дополнительно требуются `--observed-model` и `--observed-thinking`. Canonical receipt сохраняет `pending_reservation`, поэтому даже при отсутствии marker повторный reserve возвращает `reconcile_required` и `side_effect_authorized=false` и никогда повторно не авторизует side effect. Marker, receipt и вновь созданные state directory синхронизируются через `fsync`. Корень по умолчанию `$CODEX_HOME/state/auto-route-for-codex` уже durable; `AUTO_ROUTE_STATE_HOME` — только explicit override/test hook, а не условие persistence. Reservation marker содержит только hashes и bounded transfer metadata, не сохраняет raw task text и никогда не попадает в package или repository.

`reservation_lease` — это ephemeral coordination nonce и bearer capability, а не credential. Значение один раз выводится для победившей операции в private local CLI stdout или эквивалентных tool-execution detail и возвращается через process argument `--reservation-lease`; будущий совместимый интерфейс может использовать stdin. Значение должно оставаться внутри этой приватной операции. Никогда не копируйте его в task prompt, final или другой user-facing prose, package или repository, external telemetry, Issue или support report, а также durable log. Эта граница снижает риск случайного раскрытия, но не защищает lease от malicious same-user writer.

Истёкшие или stale evidence никогда не авторизуют новую reservation. Если reservation уже была надёжно записана как `pending_reservation`, пока её immutable binding была действительна, соответствующий lease после истечения evidence TTL может только подтвердить именно эту начатую операцию или пометить её `uncertain`. Это исключение не может авторизовать другой host side effect. Единственный поддерживаемый state mutation interface — CLI `transfer_state.py`. Python imports реализации и прямое изменение state file являются unsupported internals.

Timeout, несовпадение, неполный результат или неоднозначный side effect переводит состояние в `uncertain`. Нельзя повторно отправлять, создавать новый fork, выполнять исходный запрос в источнике или архивировать источник. Если destination identifier известен, разрешена только сверка этого назначения. Если fork фактически завершился успешно, но host response был потерян до возврата destination identifier, durable replay protection по-прежнему блокирует повторный fork, выполнение в источнике и архивирование источника, однако plugin не может самостоятельно обнаружить неизвестное назначение. Оставьте источник видимым и используйте host UI или канал поддержки, чтобы найти или восстановить назначение. Это предотвращает duplicate execution, но не доказывает отсутствие lost tasks. Hashes квитанции и reservation обеспечивают deterministic integrity, а не signature; malicious local writer, способный заменить local state, находится за пределами threat boundary.

## Границы безопасности публичной редакции

Включено:

- строгие JSON-схемы входа, выхода и квитанции переноса;
- детерминированная маршрутизация, bounded current-setting fallback и reservation-backed логика состояния переноса;
- сохраняющая конфиденциальность привязка к исходной задаче, которая запрещает возобновление из другого источника и несколько `transfer_id` для одного источника;
- контракт продолжения задач Codex Desktop с проверкой возможностей;
- тесты маршрутов, контрактов, негативной семантики, машины состояний и границ отказа;
- проверка публичного репозитория, конфиденциальности, переводов и релиза;
- основной английский текст, полный упрощённый китайский перевод и локализованные README.

Преднамеренно исключено:

- unbounded session scanning, извлечение task text или экспорт session content и reservation marker;
- приватные квитанции текущих настроек, приватные каталоги или локальное состояние marketplace;
- журналы выполнения, учётные данные, локальные пути, идентификаторы задач или приватная конфигурация;
- скрытая активация, автоматический перенос для `efficiency`, изменение встроенного выбора модели или запись в глобальную конфигурацию Codex;
- утверждения, что Codex CLI, IDE, cloud, API или другие agents предоставляют инструменты задач Codex Desktop.

См. [Конфиденциальность и поток данных](docs/privacy-and-data-flow.md), [Политика маршрутизации](docs/routing-policy.md) и [Совместимость](docs/compatibility.md).

## Структура репозитория

| Путь | Назначение |
|---|---|
| `.codex-plugin/plugin.json` | Манифест плагина |
| `.agents/plugins/marketplace.json` | Запись маркетплейса |
| `skills/auto-route-for-codex/` | Навык, схемы, bounded current-setting reader, маршрутизатор, reservation-backed transfer reducer и тесты |
| `docs/` | Авторитетная документация на английском языке |
| `docs/i18n/zh-CN/` | Полные переводы на упрощённый китайский язык |
| `scripts/verify_public_repo.py` | Проверки репозитория, переводов, конфиденциальности и ссылок |
| `scripts/build_release.py` | Детерминированный сборщик ZIP-архива плагина и `SHA256SUMS` |

## Проверка из чистого клона

```sh
python3 -m pip install --disable-pip-version-check --only-binary=:all: --require-hashes -r .github/requirements-ci.txt
python3 scripts/verify_public_repo.py --require-git-history
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

Успешное выполнение локальных проверок подтверждает контракт репозитория. Оно не доказывает, что каждая версия среды Codex предоставляет одинаковый интерфейс плагинов или моделей; см. [Совместимость](docs/compatibility.md).

## Документация

- [Архитектура](docs/architecture.md)
- [Установка и откат](docs/installation.md)
- [Контракт конфигурации](docs/configuration.md)
- [Конфиденциальность и поток данных](docs/privacy-and-data-flow.md)
- [Политика маршрутизации](docs/routing-policy.md)
- [Совместимость](docs/compatibility.md)
- [Устранение неполадок](docs/troubleshooting.md)
- [Часто задаваемые вопросы](docs/faq.md)

## Состояние проекта

`v0.5.0-alpha.2` усиливает конфиденциальность публичной истории, целостность зависимостей CI и подтверждение происхождения релизов. Контракт маршрутизации во время выполнения не изменён. См. [CHANGELOG.md](CHANGELOG.md) и [ROADMAP.md](ROADMAP.md).

## Участие в проекте и безопасность

Перед открытием запроса на включение изменений прочитайте [CONTRIBUTING.md](CONTRIBUTING.md). Сообщайте о проблемах безопасности через приватную систему GitHub для уведомления об уязвимостях, как описано в [SECURITY.md](SECURITY.md); не публикуйте конфиденциальные отчёты в общедоступных обсуждениях проблем.

## Лицензия

Apache License 2.0. См. [LICENSE](LICENSE) и [NOTICE](NOTICE).
