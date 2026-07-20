---
translation_of: README.md
source_revision: docs-v0.5.0-alpha.2
last_synced_version: 0.5.0-alpha.2
---

# Auto Route for Codex

**Sprache:** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | Deutsch | [Español](README.es.md)

> Community-Projekt im Alpha-Stadium. Kein offizielles Produkt von OpenAI.

Auto Route for Codex ist ein ausdrücklich zu aktivierendes Codex-Plugin, das anhand eines datenschutzbeschränkten Aufgabenprofils eine ausreichende Modellrolle, einen angemessenen Denkaufwand und eine passende Ausführungstopologie empfiehlt. Auf einem unterstützten Codex-Desktop-Host kann es eine qualitäts- oder parallelitätssensitive Aufgabe in einem Fork fortsetzen, aber nur nachdem die Host-Fähigkeits- und Evidenzprüfungen erfolgreich waren. Jede andere Umgebung fällt sicher auf eine Empfehlung in der aktuellen Aufgabe zurück.

## Warum dieses Projekt existiert

Die Wahl des Modells und der Denkaufwand sind getrennte Entscheidungen. Eine kurze, aber riskante Aufgabe kann ein leistungsstärkeres Modell erfordern, während eine lange, wiederkehrende und überprüfbare Aufgabe von einem schnelleren Modell profitieren kann. Dieses Plugin macht diese Abwägungen sichtbar, ohne die Modellwahl in einen unsichtbaren Nebeneffekt zu verwandeln.

Der öffentliche Vertrag folgt sechs Regeln:

- die Aktivierung erfolgt ausdrücklich über `$auto-route-for-codex`;
- nur aufgezählte Profilfelder erreichen den deterministischen Router;
- die aktuelle Einstellung bevorzugt host-injected evidence; wenn diese fehlt, darf der begrenzte `read_current_setting.py`-Fallback nur `current` und `current_provenance` ausgeben, und jedes `unknown`-Ergebnis bleibt recommendation-only;
- eine Aufgabenfortsetzung erfordert Codex Desktop, alle benötigten Aufgabenwerkzeuge, verifizierte Evidenz zur aktuellen Einstellung und zum Katalog sowie ein vom Host unterstütztes empfohlenes Modell und thinking;
- das Routing erfordert `host_capabilities.source_task_context=true`, und jede Übertragung benötigt unabhängig davon eine gültige `CODEX_THREAD_ID`; `transfer_state.py` leitet lokal `source_binding_sha256` ab und speichert oder gibt die rohe Quellkennung niemals aus;
- jeder Side Effect in `fork -> send -> readback -> navigate -> archive` benötigt eine eigene atomic reservation, und die Quelle darf erst archiviert werden, nachdem die bestätigte Abfolge genau ein Ziel erreicht hat.

## Schnellstart

Voraussetzungen:

- eine Codex-Oberfläche, die Plugins und den ausdrücklichen Aufruf von Skills unterstützt;
- die Codex CLI muss über `PATH` verfügbar sein;
- Zugriff auf das öffentliche Git-Repository.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.2
codex plugin add auto-route-for-codex@jacob101519
```

Starte eine neue Codex-Aufgabe, wähle **Auto Route for Codex** aus oder rufe Folgendes auf:

```text
$auto-route-for-codex Review this task and use a sufficient Codex setting.
```

Das Plugin erzeugt immer eine versionierte Entscheidung und bevorzugt eine host-injected current setting. Fehlt diese Observation und sind `CODEX_THREAD_ID` sowie ein nutzbares `CODEX_HOME` verfügbar, darf `read_current_setting.py` nur die passende lokale Sitzung unter `$CODEX_HOME/sessions` untersuchen und ein begrenztes Ergebnis `current + current_provenance` ohne Task-Text, Pfad oder Thread-ID ausgeben. Ein Fehler des Readers ergibt `unknown`. Auf einem geeigneten Codex-Desktop-Host kann eine verifizierte `quality`- oder `parallelism`-Abweichung in einem Fork mit dem empfohlenen `model` und `thinking` fortgesetzt werden; eine `efficiency`-Abweichung, eine nicht unterstützte Oberfläche, ein fehlendes Werkzeug, eine nicht unterstützte Einstellung oder `unknown|stale|uncertain` Evidenz bleibt `stay` und recommendation-only.

Das Plugin ändert weder den nativen Modellwähler noch `config.toml`, dauerhafte Standardwerte, Sandbox-Einstellungen, Genehmigungsrichtlinien, Netzwerkzugriff oder Zugangsdaten.

Jede Übertragung wird an die Quellaufgabe gebunden: Die Host-Evidenz beim Routing muss `host_capabilities.source_task_context=true` deklarieren, und zur Laufzeit ist zusätzlich eine gültige `CODEX_THREAD_ID` erforderlich; beides ist zwingend. `transfer_state.py` leitet `source_binding_sha256` lokal ab und speichert oder gibt die rohe Quellkennung niemals aus. Der Hash fließt in den quellbezogenen Sperrschlüssel, den kanonischen Beleg, `authorization_binding`, jeden Reservierungsmarker und jede Übergangsprüfung einschließlich der Archivbestätigung ein. Deshalb kann dieselbe Quelle keine zweite Übertragung mit einer anderen `transfer_id` starten, und eine andere Quelle kann die Übertragung weder fortsetzen noch bestätigen oder archivieren. Fehlender, ungültiger oder abweichender Quellkontext führt zu fail closed.

## Fähigkeitsgesteuerte Desktop-Fortsetzung

Der vollständige Pfad ist nur verfügbar, wenn alle folgenden Prüfungen erfolgreich sind:

1. Die aktuelle Oberfläche ist Codex Desktop;
2. der Host stellt kompatible Fähigkeiten für `fork_thread`, `send_message_to_thread`, `read_thread`, `navigate_to_codex_page` und `set_thread_archived` bereit;
3. Evidenz zur aktuellen Einstellung ist `verified` und aktuell, verwendet zuerst die Host-Injektion und nur bei Bedarf den begrenzten Fallback; die Evidenz zum Modellkatalog ist ebenfalls `verified` und aktuell;
4. das empfohlene `model` und `thinking` werden vom Live-Host unterstützt;
5. vor jedem Aufruf von Fork, Send, Readback, Navigation oder Archive erstellt `transfer_state.py --reserve-event` im durable default root `$CODEX_HOME/state/auto-route-for-codex` einen atomaren `O_EXCL`-Marker. `AUTO_ROUTE_STATE_HOME` ist nur ein explicit override/test hook, und der Host-Aufruf läuft bei `side_effect_authorized=true` ausschließlich mit dem von der Reservation zurückgegebenen winner-only `reservation_lease`;
6. die Prompt-Zustellung bestätigt die tatsächlich verwendeten Modell- und thinking-Overrides, das Ziel-Readback beweist, dass die bereinigte Originalanfrage den exakten Fork erreicht hat, und die Navigation gelingt, bevor Archive autorisiert wird.

Der geordnete Lebenszyklus ist:

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

Eine erfolgreiche Reservation gibt einen winner-only `reservation_lease` zurück. Nach dem Host Side Effect bestätigt `--event` mit demselben `--router-input` und übergibt den Lease als `--reservation-lease`; `prompt_delivery_confirmed` erfordert zusätzlich `--observed-model` und `--observed-thinking`. Der canonical receipt speichert `pending_reservation` dauerhaft, sodass selbst bei fehlendem Marker eine wiederholte Reservation `reconcile_required` und `side_effect_authorized=false` zurückgibt und den Side Effect nie erneut autorisiert. Marker, Receipt und neu erstellte State-Verzeichnisse werden mit `fsync` synchronisiert. Der Standard-Root `$CODEX_HOME/state/auto-route-for-codex` ist bereits durable; `AUTO_ROUTE_STATE_HOME` ist nur ein explicit override/test hook und für Persistence nicht erforderlich. Reservation-Marker enthalten nur Hashes und begrenzte Transfermetadaten, speichern keinen raw task text und gelangen nie in das Package oder Repository.

`reservation_lease` ist eine flüchtige coordination nonce und bearer capability, kein credential. Sie wird einmal für die gewinnende Operation in privater lokaler CLI-stdout oder einem gleichwertigen Tool-Ausführungsdetail ausgegeben und über das Prozessargument `--reservation-lease` zurückgegeben; eine künftige kompatible Schnittstelle kann stattdessen stdin verwenden. Der Wert muss innerhalb dieser privaten Operation bleiben. Er darf niemals in einen Task-Prompt, final oder andere benutzersichtbare Texte, Package oder Repository, externe Telemetrie, Issue- oder Supportberichte oder dauerhafte Logs kopiert werden. Diese Grenze reduziert versehentliche Offenlegung, schützt den Lease jedoch nicht vor einem malicious same-user writer.

Abgelaufene oder anderweitig stale Evidenz autorisiert niemals eine neue Reservation. Wenn eine Reservation bereits bei gültiger immutable binding dauerhaft als `pending_reservation` aufgezeichnet wurde, darf der passende Lease nach Ablauf der Evidenz-TTL nur diese exakte Operation bestätigen oder als `uncertain` markieren. Dadurch darf kein weiterer Host Side Effect autorisiert werden. Die einzige unterstützte Mutationsschnittstelle ist die CLI von `transfer_state.py`. Python-Imports der Implementierung und direkte Änderungen an State-Dateien sind unsupported internals.

Ein Timeout, eine Abweichung, ein unvollständiges Ergebnis oder ein mehrdeutiger Nebeneffekt führt zu `uncertain`. Das Plugin darf nicht erneut senden, erneut forken, die Originalanfrage in der Quelle ausführen oder die Quelle archivieren. Wenn eine Zielkennung bekannt ist, darf es nur dieses Ziel abgleichen. Wenn der fork tatsächlich erfolgreich war, aber die Host-Antwort verloren ging, bevor eine Zielkennung zurückgegeben wurde, blockiert der durable replay protection weiterhin erneutes Forken, die Ausführung in der Quelle und die Archivierung der Quelle; das Plugin kann das unbekannte Ziel jedoch nicht selbst ermitteln. Lassen Sie die Quelle sichtbar und verwenden Sie die Host-UI oder den Support-Kanal, um das Ziel zu finden oder wiederherzustellen. Dies verhindert doppelte Ausführung, beweist aber nicht, dass keine Aufgaben verloren gehen. Receipt- und Reservation-Hashes liefern deterministic integrity, keine signature; ein malicious local writer, der den lokalen Zustand ersetzen kann, liegt außerhalb der threat boundary.

## Öffentliche Sicherheitsgrenze

Enthalten:

- strenge JSON-Schemas für Eingabe, Ausgabe und Transferbelege;
- deterministisches Routing, begrenzter Current-Setting-Fallback und reservation-backed Transferzustandslogik;
- eine datenschutzwahrende Bindung an die Quellaufgabe, die das Fortsetzen aus einer anderen Quelle und mehrere `transfer_id`-Werte für eine Quelle verhindert;
- ein fähigkeitsgesteuerter Codex-Desktop-Vertrag zur Aufgabenfortsetzung;
- Routing-, Vertrags-, semantische Negativ-, Zustandsmaschinen- und Fehlergrenzentests;
- Prüfungen für öffentliches Repository, Datenschutz, Übersetzung und Release;
- maßgebliche englische Dokumentation, eine vollständige vereinfachte chinesische Übersetzung und lokalisierte README-Einstiege.

Bewusst ausgeschlossen:

- unbounded session scanning, Extraktion von Task-Text oder Export von Sitzungsinhalten und Reservation-Markern;
- private Belege zur aktuellen Einstellung, private Kataloge oder lokaler Marketplace-Zustand;
- Laufzeitprotokolle, Zugangsdaten, lokale Pfade, Aufgabenkennungen oder private Konfigurationen;
- versteckte Aktivierung, automatische Übertragung für `efficiency`, Änderungen am nativen Modellwähler oder Schreibzugriffe auf die globale Codex-Konfiguration;
- Behauptungen, dass Codex CLI, IDE, Cloud, API oder andere Agents Codex-Desktop-Aufgabenwerkzeuge bereitstellen.

Siehe [Datenschutz und Datenfluss](docs/privacy-and-data-flow.md), [Routing-Richtlinie](docs/routing-policy.md) und [Kompatibilität](docs/compatibility.md).

## Repository-Übersicht

| Pfad | Zweck |
|---|---|
| `.codex-plugin/plugin.json` | Plugin-Manifest |
| `.agents/plugins/marketplace.json` | Marketplace-Eintrag |
| `skills/auto-route-for-codex/` | Skill, Schemas, begrenzter Current-Setting-Reader, Router, reservation-backed Transfer-Reducer und Tests |
| `docs/` | Maßgebliche englische Dokumentation |
| `docs/i18n/zh-CN/` | Vollständige Übersetzungen in vereinfachtes Chinesisch |
| `scripts/verify_public_repo.py` | Prüfungen für Repository, Übersetzung, Datenschutz und Links |
| `scripts/build_release.py` | Deterministischer Generator für das Plugin-ZIP und `SHA256SUMS` |

## Überprüfung aus einem sauberen Klon

```sh
python3 -m pip install --disable-pip-version-check --only-binary=:all: --require-hashes -r .github/requirements-ci.txt
python3 scripts/verify_public_repo.py --require-git-history
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

Erfolgreiche lokale Prüfungen bestätigen den Repository-Vertrag. Sie beweisen nicht, dass jede Version des Codex-Hosts dieselbe Plugin- oder Modelloberfläche bereitstellt; siehe [Kompatibilität](docs/compatibility.md).

## Dokumentation

- [Architektur](docs/architecture.md)
- [Installation und Rollback](docs/installation.md)
- [Konfigurationsvertrag](docs/configuration.md)
- [Datenschutz und Datenfluss](docs/privacy-and-data-flow.md)
- [Routing-Richtlinie](docs/routing-policy.md)
- [Kompatibilität](docs/compatibility.md)
- [Fehlerbehebung](docs/troubleshooting.md)
- [FAQ](docs/faq.md)

## Projektstatus

`v0.5.0-alpha.2` stärkt den Datenschutz der öffentlichen Historie, die Integrität der CI-Abhängigkeiten und die Herkunftsnachweise für Releases. Der Laufzeit-Routingvertrag bleibt unverändert. Siehe [CHANGELOG.md](CHANGELOG.md) und [ROADMAP.md](ROADMAP.md).

## Beiträge und Sicherheit

Lies [CONTRIBUTING.md](CONTRIBUTING.md), bevor du einen Pull Request öffnest. Melde Sicherheitsprobleme über GitHubs private Schwachstellenmeldung, wie in [SECURITY.md](SECURITY.md) beschrieben; veröffentliche sensible Berichte nicht in einer öffentlichen Issue.

## Lizenz

Apache License 2.0. Siehe [LICENSE](LICENSE) und [NOTICE](NOTICE).
