---
translation_of: README.md
source_revision: docs-v0.5.0-alpha.1
last_synced_version: 0.5.0-alpha.1
---

# Auto Route for Codex

**Idioma:** [English](README.md) | [Português (Brasil)](README.pt-BR.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | Español

> Proyecto comunitario en fase alfa. No es un producto oficial de OpenAI.

Auto Route for Codex es un plugin de Codex de activación explícita que recomienda un rol de modelo, un nivel de esfuerzo de razonamiento y una topología de ejecución suficientes a partir de un perfil de tarea con límites de privacidad. En un host compatible de Codex Desktop puede continuar en un fork una tarea sensible a `quality` o `parallelism`, pero solo después de superar las comprobaciones de capacidades y evidencia. Cualquier otro entorno se degrada de forma segura a una recomendación en la tarea actual.

## Por qué existe este proyecto

La elección del modelo y el esfuerzo de razonamiento son decisiones independientes. Una tarea breve pero arriesgada puede necesitar un modelo más potente, mientras que un trabajo largo, repetitivo y verificable puede beneficiarse de uno más rápido. Este plugin hace explícitas esas decisiones sin convertir la selección del modelo en un efecto secundario invisible.

El contrato público sigue seis reglas:

- la activación es explícita mediante `$auto-route-for-codex`;
- solo los campos enumerados del perfil llegan al enrutador determinista;
- la configuración actual prioriza la evidencia inyectada por el host; cuando no existe, el fallback acotado `read_current_setting.py` solo puede emitir `current` y `current_provenance`, y cualquier resultado `unknown` permanece recommendation-only;
- la continuación requiere Codex Desktop, todas las herramientas de tarea necesarias, evidencia verificada de la configuración actual y del catálogo, y valores recomendados de modelo y thinking compatibles con el host;
- el enrutamiento exige `host_capabilities.source_task_context=true`, y cada transferencia requiere de forma independiente un `CODEX_THREAD_ID` válido; `transfer_state.py` deriva localmente `source_binding_sha256` y nunca conserva ni muestra el identificador de origen sin procesar;
- cada efecto secundario de `fork -> send -> readback -> navigate -> archive` requiere su propia reserva atómica, y el origen solo puede archivarse después de que la secuencia confirmada alcance un único destino.

## Inicio rápido

Requisitos previos:

- una interfaz de Codex compatible con plugins y con la invocación explícita de skills;
- la Codex CLI disponible en `PATH`;
- acceso al repositorio Git público.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

Inicia una nueva tarea de Codex, selecciona **Auto Route for Codex** o invoca:

```text
$auto-route-for-codex Review this task and use a sufficient Codex setting.
```

El plugin siempre produce una decisión versionada y prioriza una configuración actual inyectada por el host. Si falta esa observación y están disponibles `CODEX_THREAD_ID` y un `CODEX_HOME` utilizable, `read_current_setting.py` solo puede inspeccionar la sesión local coincidente en `$CODEX_HOME/sessions` y emitir un resultado acotado `current + current_provenance` sin texto de la tarea, ruta ni identificador del hilo. Un fallo del lector devuelve `unknown`. En un host compatible de Codex Desktop, una discrepancia verificada de `quality` o `parallelism` puede continuar en un fork con los valores recomendados de `model` y `thinking`; una discrepancia de `efficiency`, una superficie no compatible, una herramienta ausente, una configuración no compatible o evidencia `unknown|stale|uncertain` permanece `stay` y recommendation-only.

El plugin no modifica el selector nativo de modelo, `config.toml`, valores predeterminados persistentes, sandbox, política de aprobación, acceso de red ni credenciales.

Cada transferencia queda vinculada a la tarea de origen: la evidencia del host durante el enrutamiento debe declarar `host_capabilities.source_task_context=true`, y en ejecución también se exige un `CODEX_THREAD_ID` válido; ambos son obligatorios. `transfer_state.py` deriva `source_binding_sha256` de forma local y nunca persiste ni muestra el identificador original sin procesar. El hash forma parte de la clave de bloqueo por origen, el recibo canónico, `authorization_binding`, cada marcador de reserva y toda validación de transición, incluida la confirmación de archivado. Por ello, el mismo origen no puede iniciar una segunda transferencia con otro `transfer_id`, y un origen distinto no puede reanudar, confirmar ni archivar esa transferencia. Un contexto de origen ausente, inválido o distinto falla de forma cerrada.

## Continuación de Desktop protegida por capacidades

La ruta completa solo está disponible cuando se cumplen todas estas comprobaciones:

1. la superficie actual es Codex Desktop;
2. el host expone capacidades compatibles para `fork_thread`, `send_message_to_thread`, `read_thread`, `navigate_to_codex_page` y `set_thread_archived`;
3. la evidencia de configuración actual está `verified` y vigente, usa primero la inyección del host y solo cuando es necesario el fallback acotado; la evidencia del catálogo de modelos también está `verified` y vigente;
4. el host activo admite los valores recomendados de `model` y `thinking`;
5. antes de cada llamada de fork, envío, lectura, navegación o archivado, `transfer_state.py --reserve-event` crea un marcador atómico `O_EXCL` en la durable default root `$CODEX_HOME/state/auto-route-for-codex`. `AUTO_ROUTE_STATE_HOME` solo es un explicit override/test hook, y la llamada al host solo se ejecuta con `side_effect_authorized=true` y el winner-only `reservation_lease` devuelto por la reserva;
6. la entrega del prompt confirma los overrides reales de modelo y thinking, la lectura del destino demuestra que la solicitud original limpia llegó al fork exacto, y la navegación tiene éxito antes de autorizar el archivado.

El ciclo de vida ordenado es:

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

Una reserva correcta devuelve un winner-only `reservation_lease`. Después del efecto secundario del host, la confirmación mediante `--event` usa el mismo `--router-input` y pasa el lease como `--reservation-lease`; `prompt_delivery_confirmed` requiere además `--observed-model` y `--observed-thinking`. El canonical receipt conserva `pending_reservation`, por lo que incluso sin el marcador una reserva repetida devuelve `reconcile_required` y `side_effect_authorized=false` y nunca vuelve a autorizar el efecto secundario. El marcador, el recibo y los directorios de estado recién creados reciben `fsync`. La raíz predeterminada `$CODEX_HOME/state/auto-route-for-codex` ya es durable; `AUTO_ROUTE_STATE_HOME` solo es un explicit override/test hook, no un requisito de persistencia. Los marcadores de reserva contienen solo hashes y metadatos acotados de transferencia, no guardan raw task text y nunca entran en el paquete ni en el repositorio.

`reservation_lease` es un nonce efímero de coordinación y una bearer capability, no una credential. Se emite una sola vez a la operación ganadora en el stdout privado de la CLI local o en un detalle equivalente de ejecución de herramienta, y se devuelve mediante el argumento de proceso `--reservation-lease`; una interfaz compatible futura puede usar stdin. El valor debe permanecer dentro de esa operación privada. Nunca debe copiarse en un prompt de tarea, en el texto final o cualquier texto visible para el usuario, en el paquete o repositorio, en telemetría externa, en un Issue o informe de soporte, ni en un log persistente. Este límite reduce la divulgación accidental, pero no protege el lease de un malicious same-user writer.

La evidencia expirada o stale nunca autoriza una reserva nueva. Si una reserva ya se registró de forma durable como `pending_reservation` mientras su immutable binding era válida, el lease correspondiente solo puede confirmar esa operación exacta o marcarla como `uncertain` después del TTL de la evidencia. Esta excepción no puede autorizar otro efecto secundario del host. La única interfaz de mutación admitida es la CLI de `transfer_state.py`. Los imports de Python de la implementación y la modificación directa de archivos de estado son unsupported internals.

Un timeout, una discrepancia, un resultado incompleto o un efecto ambiguo entra en `uncertain`. El plugin no debe reenviar, crear otro fork, ejecutar la solicitud original en el origen ni archivarlo. Cuando se conoce un identificador de destino, solo puede reconciliar ese destino. Si el fork tuvo éxito pero se perdió la respuesta del host antes de que se devolviera un identificador de destino, la durable replay protection sigue bloqueando otro fork, la ejecución en el origen y el archivado del origen, pero el plugin no puede descubrir por sí mismo el destino desconocido. Mantenga visible el origen y use la UI del host o el canal de soporte para localizar o recuperar el destino. Esto evita la ejecución duplicada, pero no demuestra que no se pierda ninguna tarea. Los hashes del recibo y de la reserva aportan deterministic integrity, no una signature; un malicious local writer capaz de sustituir el estado local queda fuera de la threat boundary.

## Límite de seguridad de la edición pública

Incluye:

- schemas JSON estrictos de entrada, salida y recibo de transferencia;
- enrutamiento determinista, fallback acotado de configuración actual y lógica de estado de transferencia respaldada por reservas;
- vinculación del origen respetuosa con la privacidad, que impide reanudar desde otro origen y usar varios valores de `transfer_id` para un mismo origen;
- un contrato de continuación de tareas en Codex Desktop protegido por capacidades;
- pruebas de ruta, contrato, casos semánticos negativos, máquina de estados y límites de fallo;
- verificación del repositorio público, privacidad, traducción y publicación;
- documentación inglesa autorizada, traducción completa al chino simplificado y entradas README localizadas.

Excluye intencionadamente:

- escaneo ilimitado de sesiones, extracción del texto de la tarea o exportación del contenido de sesión y de los marcadores de reserva;
- recibos privados de configuración actual, catálogos privados o estado local del marketplace;
- registros de ejecución, credenciales, rutas locales, identificadores de tareas o configuración privada;
- activación oculta, transferencia automática por `efficiency`, cambios del selector nativo de modelo o escrituras en la configuración global de Codex;
- afirmaciones de que Codex CLI, IDE, cloud, API u otros agents exponen herramientas de tarea de Codex Desktop.

Consulta [Privacidad y flujo de datos](docs/privacy-and-data-flow.md), [Política de enrutamiento](docs/routing-policy.md) y [Compatibilidad](docs/compatibility.md).

## Mapa del repositorio

| Ruta | Propósito |
|---|---|
| `.codex-plugin/plugin.json` | Manifiesto del plugin |
| `.agents/plugins/marketplace.json` | Entrada del marketplace |
| `skills/auto-route-for-codex/` | Skill, schemas, lector acotado de configuración actual, enrutador, reductor de transferencia respaldado por reservas y pruebas |
| `docs/` | Documentación en inglés, fuente de referencia |
| `docs/i18n/zh-CN/` | Traducciones completas al chino simplificado |
| `scripts/verify_public_repo.py` | Comprobaciones del repositorio, la traducción, la privacidad y los enlaces |
| `scripts/build_release.py` | Generador determinista del ZIP del plugin y de `SHA256SUMS` |

## Verificación desde un clon limpio

```sh
python3 -m pip install --disable-pip-version-check PyYAML==6.0.3 jsonschema==4.26.0
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

`v0.5.0-alpha.1` es la primera versión alfa pública con continuación de tareas en Codex Desktop protegida por capacidades. La API y la estructura del paquete pueden cambiar antes de una versión estable. Consulta [CHANGELOG.md](CHANGELOG.md) y [ROADMAP.md](ROADMAP.md).

## Contribuciones y seguridad

Lee [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir un pull request. Informa de los problemas de seguridad mediante el sistema privado de informes de vulnerabilidades de GitHub, tal como se describe en [SECURITY.md](SECURITY.md); no publiques informes confidenciales en una issue pública.

## Licencia

Apache License 2.0. Consulta [LICENSE](LICENSE) y [NOTICE](NOTICE).
