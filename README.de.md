---
translation_of: README.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# Auto Route for Codex

**Sprache:** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | Deutsch | [Español](README.es.md)

> Community-Projekt im Alpha-Stadium. Kein offizielles Produkt von OpenAI.

Auto Route for Codex ist ein ausdrücklich zu aktivierendes Codex-Plugin, das anhand eines datenschutzbeschränkten Aufgabenprofils eine ausreichende Modellrolle, einen angemessenen Denkaufwand und eine passende Ausführungstopologie empfiehlt. Die öffentliche Edition ist bewusst auf Empfehlungen beschränkt: Sie verzweigt, erstellt, navigiert, archiviert oder wiederholt niemals eine Aufgabe.

## Warum dieses Projekt existiert

Die Wahl des Modells und der Denkaufwand sind getrennte Entscheidungen. Eine kurze, aber riskante Aufgabe kann ein leistungsstärkeres Modell erfordern, während eine lange, wiederkehrende und überprüfbare Aufgabe von einem schnelleren Modell profitieren kann. Dieses Plugin macht diese Abwägungen sichtbar, ohne die Modellwahl in einen unsichtbaren Nebeneffekt zu verwandeln.

Der öffentliche Vertrag folgt vier Regeln:

- die Aktivierung erfolgt ausdrücklich über `$auto-route-for-codex`;
- nur aufgezählte Profilfelder erreichen den deterministischen Router;
- eine Empfehlung wird ausschließlich anhand der vom Host bereitgestellten Modell- und thinking-Werte aufgelöst;
- jede öffentliche Entscheidung bleibt `stay + none|efficiency + none + keep`.

## Schnellstart

Voraussetzungen:

- eine Codex-Oberfläche, die Plugins und den ausdrücklichen Aufruf von Skills unterstützt;
- die Codex CLI muss über `PATH` verfügbar sein;
- Zugriff auf das öffentliche Git-Repository.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

Starte eine neue Codex-Aufgabe, wähle **Auto Route for Codex** aus oder rufe Folgendes auf:

```text
$auto-route-for-codex Review this task and recommend a sufficient Codex setting.
```

Das Plugin gibt eine versionierte Empfehlung zurück. Es ändert weder das Modell noch die Einstellungen der aktuellen Aufgabe.

## Öffentliche Sicherheitsgrenze

Enthalten:

- strenge JSON-Schemas für Ein- und Ausgabe;
- deterministische Routing-Logik;
- Tests, die ausschließlich Empfehlungen erzeugen, sowie semantische Negativfälle;
- Skripte zur Überprüfung des öffentlichen Repositorys und des Releases;
- englische Dokumentation und vollständige Übersetzungen in vereinfachtes Chinesisch.

Bewusst ausgeschlossen:

- lokale Leser für Sitzungsdateien;
- private Belege oder Kataloge der aktuellen Einstellung;
- Orchestrierung zum Verzweigen, Navigieren, Archivieren und Wiederholen von Aufgaben;
- Laufzeitprotokolle, Zugangsdaten, lokale Pfade, Aufgabenkennungen oder private Konfigurationen;
- automatische Modelländerungen oder Schreibzugriffe auf die globale Codex-Konfiguration.

Siehe [Datenschutz und Datenfluss](docs/privacy-and-data-flow.md) und [Routing-Richtlinie](docs/routing-policy.md).

## Repository-Übersicht

| Pfad | Zweck |
|---|---|
| `.codex-plugin/plugin.json` | Plugin-Manifest |
| `.agents/plugins/marketplace.json` | Marketplace-Eintrag |
| `skills/auto-route-for-codex/` | Skill, Schemas, Router und Tests |
| `docs/` | Maßgebliche englische Dokumentation |
| `docs/i18n/zh-CN/` | Vollständige Übersetzungen in vereinfachtes Chinesisch |
| `scripts/verify_public_repo.py` | Prüfungen für Repository, Übersetzung, Datenschutz und Links |
| `scripts/build_release.py` | Deterministischer Generator für das Plugin-ZIP und `SHA256SUMS` |

## Überprüfung aus einem sauberen Klon

```sh
python3 scripts/verify_public_repo.py
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

`v0.4.0-alpha.1` ist die erste öffentliche Alpha-Version. Die API und die Paketstruktur können sich vor einer stabilen Version ändern. Siehe [CHANGELOG.md](CHANGELOG.md) und [ROADMAP.md](ROADMAP.md).

## Beiträge und Sicherheit

Lies [CONTRIBUTING.md](CONTRIBUTING.md), bevor du einen Pull Request öffnest. Melde Sicherheitsprobleme über GitHubs private Schwachstellenmeldung, wie in [SECURITY.md](SECURITY.md) beschrieben; veröffentliche sensible Berichte nicht in einer öffentlichen Issue.

## Lizenz

Apache License 2.0. Siehe [LICENSE](LICENSE) und [NOTICE](NOTICE).
