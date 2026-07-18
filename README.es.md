---
translation_of: README.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# Auto Route for Codex

**Idioma:** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | Español

> Proyecto comunitario en fase alfa. No es un producto oficial de OpenAI.

Auto Route for Codex es un plugin de Codex de activación explícita que recomienda un rol de modelo, un nivel de esfuerzo de razonamiento y una topología de ejecución suficientes a partir de un perfil de tarea con límites de privacidad. La edición pública está deliberadamente limitada a recomendaciones: nunca bifurca, crea, navega, archiva ni repite una tarea.

## Por qué existe este proyecto

La elección del modelo y el esfuerzo de razonamiento son decisiones independientes. Una tarea breve pero arriesgada puede necesitar un modelo más potente, mientras que un trabajo largo, repetitivo y verificable puede beneficiarse de uno más rápido. Este plugin hace explícitas esas decisiones sin convertir la selección del modelo en un efecto secundario invisible.

El contrato público sigue cuatro reglas:

- la activación es explícita mediante `$auto-route-for-codex`;
- solo los campos enumerados del perfil llegan al enrutador determinista;
- una recomendación se resuelve únicamente con los valores de modelo y thinking proporcionados por el host;
- toda decisión pública permanece como `stay + none|efficiency + none + keep`.

## Inicio rápido

Requisitos previos:

- una interfaz de Codex compatible con plugins y con la invocación explícita de skills;
- la Codex CLI disponible en `PATH`;
- acceso al repositorio Git público.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

Inicia una nueva tarea de Codex, selecciona **Auto Route for Codex** o invoca:

```text
$auto-route-for-codex Review this task and recommend a sufficient Codex setting.
```

El plugin devuelve una recomendación versionada. No cambia el modelo ni la configuración de la tarea actual.

## Límite de seguridad de la edición pública

Incluye:

- schemas JSON estrictos de entrada y salida;
- lógica de enrutamiento determinista;
- pruebas limitadas a recomendaciones y casos semánticos negativos;
- scripts de verificación del repositorio público y de la publicación;
- documentación en inglés y traducciones completas al chino simplificado.

Excluye intencionadamente:

- lectores locales de archivos de sesión;
- recibos o catálogos privados de la configuración actual;
- orquestación de bifurcación, navegación, archivado y repetición de tareas;
- registros de ejecución, credenciales, rutas locales, identificadores de tareas o configuración privada;
- cambios automáticos de modelo o escrituras en la configuración global de Codex.

Consulta [Privacidad y flujo de datos](docs/privacy-and-data-flow.md) y [Política de enrutamiento](docs/routing-policy.md).

## Mapa del repositorio

| Ruta | Propósito |
|---|---|
| `.codex-plugin/plugin.json` | Manifiesto del plugin |
| `.agents/plugins/marketplace.json` | Entrada del marketplace |
| `skills/auto-route-for-codex/` | Skill, schemas, enrutador y pruebas |
| `docs/` | Documentación en inglés, fuente de referencia |
| `docs/i18n/zh-CN/` | Traducciones completas al chino simplificado |
| `scripts/verify_public_repo.py` | Comprobaciones del repositorio, la traducción, la privacidad y los enlaces |
| `scripts/build_release.py` | Generador determinista del ZIP del plugin y de `SHA256SUMS` |

## Verificación desde un clon limpio

```sh
python3 scripts/verify_public_repo.py
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

La superación de las comprobaciones locales valida el contrato del repositorio. No demuestra que todas las versiones del host de Codex expongan la misma interfaz de plugin o modelo; consulta [Compatibilidad](docs/compatibility.md).

## Documentación

- [Arquitectura](docs/architecture.md)
- [Instalación y reversión](docs/installation.md)
- [Contrato de configuración](docs/configuration.md)
- [Privacidad y flujo de datos](docs/privacy-and-data-flow.md)
- [Política de enrutamiento](docs/routing-policy.md)
- [Compatibilidad](docs/compatibility.md)
- [Solución de problemas](docs/troubleshooting.md)
- [Preguntas frecuentes](docs/faq.md)

## Estado del proyecto

`v0.4.0-alpha.1` es la primera versión alfa pública. La API y la estructura del paquete pueden cambiar antes de una versión estable. Consulta [CHANGELOG.md](CHANGELOG.md) y [ROADMAP.md](ROADMAP.md).

## Contribuciones y seguridad

Lee [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir un pull request. Informa de los problemas de seguridad mediante el sistema privado de informes de vulnerabilidades de GitHub, tal como se describe en [SECURITY.md](SECURITY.md); no publiques informes confidenciales en una issue pública.

## Licencia

Apache License 2.0. Consulta [LICENSE](LICENSE) y [NOTICE](NOTICE).
