---
translation_of: README.md
source_revision: docs-v0.5.0-alpha.2
last_synced_version: 0.5.0-alpha.2
---

# Auto Route for Codex

**Idioma:** [English](README.md) | Português (Brasil) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Projeto comunitário em fase alfa. Não é um produto oficial da OpenAI.

Auto Route for Codex é um plugin do Codex com ativação explícita que recomenda uma função de modelo, um nível de esforço de raciocínio e uma topologia de execução suficientes a partir de um perfil de tarefa com limites de privacidade. Em um host compatível do Codex Desktop, ele pode continuar uma tarefa sensível a `quality` ou `parallelism` em um fork somente depois que os gates de capacidade e evidência forem aprovados. Qualquer outro ambiente recua com segurança para uma recomendação na tarefa atual.

## Por que este projeto existe

A escolha do modelo e o esforço de raciocínio são decisões distintas. Uma tarefa curta, porém arriscada, pode exigir um modelo mais forte, enquanto um trabalho longo, repetitivo e verificável pode se beneficiar de um modelo mais rápido. Este plugin torna essas escolhas explícitas sem transformar a seleção do modelo em um efeito colateral invisível.

O contrato público segue seis regras:

- a ativação é explícita por meio de `$auto-route-for-codex`;
- somente os campos enumerados do perfil chegam ao roteador determinístico;
- a configuração atual prioriza a evidência injetada pelo host; quando ela estiver ausente, o fallback delimitado `read_current_setting.py` poderá emitir somente `current` e `current_provenance`, e qualquer resultado `unknown` permanecerá recommendation-only;
- a continuação exige Codex Desktop, todas as ferramentas de tarefa necessárias, evidência verificada da configuração atual e do catálogo, e modelo e thinking recomendados compatíveis com o host;
- o roteamento exige `host_capabilities.source_task_context=true`, e cada transferência exige de forma independente um `CODEX_THREAD_ID` válido; `transfer_state.py` deriva `source_binding_sha256` localmente e nunca persiste nem exibe o identificador de origem bruto;
- cada side effect de `fork -> send -> readback -> navigate -> archive` exige sua própria reserva atômica, e a origem só pode ser arquivada depois que a sequência confirmada chegar a um único destino.

## Início rápido

Pré-requisitos:

- uma interface do Codex que ofereça suporte a plugins e à invocação explícita de skills;
- a Codex CLI disponível no `PATH`;
- acesso ao repositório Git público.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.5.0-alpha.2
codex plugin add auto-route-for-codex@jacob101519
```

Inicie uma nova tarefa do Codex, selecione **Auto Route for Codex** ou invoque:

```text
$auto-route-for-codex Review this task and use a sufficient Codex setting.
```

O plugin sempre produz uma decisão versionada. Ele prioriza uma configuração atual injetada pelo host. Se essa observação estiver ausente e `CODEX_THREAD_ID` mais um `CODEX_HOME` utilizável estiverem disponíveis, `read_current_setting.py` poderá inspecionar somente a sessão local correspondente em `$CODEX_HOME/sessions` e emitir um resultado delimitado `current + current_provenance`, sem texto da tarefa, caminho ou identificador da thread. Uma falha do leitor retorna `unknown`. Em um host Codex Desktop compatível, um mismatch verificado de `quality` ou `parallelism` pode continuar em um fork com `model` e `thinking` recomendados; um mismatch de `efficiency`, surface não suportada, ferramenta ausente, configuração não suportada ou evidência `unknown|stale|uncertain` permanece `stay` e recommendation-only.

O plugin não altera o seletor nativo de modelo, `config.toml`, padrões persistentes, sandbox, política de aprovação, acesso de rede ou credenciais.

Cada transferência usa uma vinculação à tarefa de origem: a evidência do host no roteamento deve declarar `host_capabilities.source_task_context=true`, e a execução também exige um `CODEX_THREAD_ID` válido; ambos são obrigatórios. `transfer_state.py` deriva `source_binding_sha256` localmente e nunca persiste nem exibe o identificador bruto da origem. O hash participa da chave de bloqueio por origem, do recibo canônico, de `authorization_binding`, de cada marcador de reserva e de toda validação de transição, inclusive no arquivamento. Assim, a mesma origem não pode iniciar outra transferência com um `transfer_id` diferente, e outra origem não pode retomar, confirmar ou arquivar essa transferência. Contexto ausente, inválido ou incompatível falha de forma fechada.

## Continuação de Desktop protegida por capacidades

O caminho completo só está disponível quando todas estas verificações passam:

1. a surface atual é Codex Desktop;
2. o host expõe capacidades compatíveis para `fork_thread`, `send_message_to_thread`, `read_thread`, `navigate_to_codex_page` e `set_thread_archived`;
3. a evidência da configuração atual está `verified` e vigente, usando primeiro a injeção do host ou o fallback delimitado somente quando necessário, e a evidência do catálogo de modelos também está `verified` e vigente;
4. o host ativo oferece suporte aos valores recomendados de `model` e `thinking`;
5. antes de cada chamada de fork, envio, readback, navegação ou archive, `transfer_state.py --reserve-event` cria um marcador atômico `O_EXCL` na raiz durável padrão `$CODEX_HOME/state/auto-route-for-codex`; `AUTO_ROUTE_STATE_HOME` é somente um override/test hook explícito, e a chamada do host só é executada quando `side_effect_authorized=true`, usando o `reservation_lease` exclusivo do vencedor retornado pela reserva;
6. a confirmação da entrega comprova os overrides reais de model e thinking, o readback do destino comprova que a solicitação original limpa chegou ao fork exato, e a navegação é concluída antes da autorização para archive.

O ciclo de vida ordenado é:

```text
planned
  -> fork_created
  -> prompt_delivery_confirmed
  -> destination_readback_confirmed
  -> navigation_confirmed
  -> source_archive_confirmed
```

Uma reserva bem-sucedida retorna um `reservation_lease` exclusivo do vencedor; depois do side effect do host, a confirmação via `--event` usa o mesmo `--router-input` e passa esse lease como `--reservation-lease`. `prompt_delivery_confirmed` também exige `--observed-model` e `--observed-thinking`. O recibo canônico persiste `pending_reservation`; portanto, mesmo sem o marcador, uma reserva repetida retorna `reconcile_required` e `side_effect_authorized=false`, nunca reautoriza o side effect. O marcador, o recibo e os diretórios de estado recém-criados recebem `fsync`. A raiz padrão `$CODEX_HOME/state/auto-route-for-codex` já é durável; `AUTO_ROUTE_STATE_HOME` é apenas um override/test hook explícito, não um requisito para persistência. Os marcadores contêm somente hashes e metadados delimitados da transferência, nunca `raw task text`, e jamais entram no pacote ou repositório.

`reservation_lease` é um nonce efêmero de coordenação e uma bearer capability, não uma credential. Ele é emitido uma única vez para a operação vencedora no stdout privado da CLI local ou em detalhe equivalente da execução da ferramenta, e é devolvido pelo argumento de processo `--reservation-lease`; uma interface compatível futura pode usar stdin. O valor deve permanecer dentro dessa operação privada. Nunca o copie para um prompt de tarefa, texto final ou outro texto visível ao usuário, pacote ou repositório, telemetria externa, Issue ou relatório de suporte, nem log durável. Esse limite reduz divulgação acidental, mas não protege o lease de um malicious same-user writer.

Evidência expirada ou stale nunca autoriza uma nova reserva. Se uma reserva já foi registrada de forma durável como `pending_reservation` enquanto sua immutable binding era válida, o lease correspondente só pode confirmar essa operação exata ou marcá-la como `uncertain` após o TTL da evidência. Essa exceção não pode autorizar outro side effect do host. A única interface de mutação compatível é a CLI de `transfer_state.py`. Imports Python da implementação e modificação direta de arquivos de estado são unsupported internals.

Um timeout, mismatch, resultado incompleto ou side effect ambíguo entra em `uncertain`. O plugin não deve reenviar, criar outro fork, executar a solicitação original na origem ou arquivá-la. Quando um identificador de destino é conhecido, ele só pode reconciliar esse destino. Se o fork realmente teve sucesso, mas a resposta do host foi perdida antes de qualquer identificador de destino ser retornado, a durable replay protection ainda bloqueia outro fork, a execução na origem e o arquivamento da origem, mas o plugin não consegue descobrir sozinho o destino desconhecido. Mantenha a origem visível e use a UI do host ou o canal de suporte para localizar ou recuperar o destino. Isso impede execução duplicada, mas não prova zero lost tasks. Os hashes do recibo e da reserva fornecem deterministic integrity, não uma signature; um malicious local writer capaz de substituir o estado local está fora da threat boundary.

## Limite de segurança da edição pública

Incluído:

- schemas JSON rigorosos de entrada, saída e recibo de transferência;
- roteamento determinístico, fallback delimitado da configuração atual e lógica de estado de transferência respaldada por reservas;
- vinculação da tarefa de origem com preservação de privacidade, que impede retomar de outra origem e usar vários valores de `transfer_id` para uma mesma origem;
- contrato de continuação de tarefas no Codex Desktop protegido por capacidades;
- testes de rota, contrato, semântica negativa, máquina de estados e limites de falha;
- verificação de repositório público, privacidade, tradução e release;
- documentação inglesa autorizada, tradução completa para chinês simplificado e entradas README localizadas.

Excluído intencionalmente:

- varredura ilimitada de sessões, extração do texto da tarefa ou exportação do conteúdo de sessões e dos marcadores de reserva;
- recibos privados da configuração atual, catálogos privados ou estado local do marketplace;
- logs de execução, credenciais, caminhos locais, identificadores de tarefas ou configurações privadas;
- ativação oculta, transferência automática por `efficiency`, alterações do seletor nativo de modelo ou gravações na configuração global do Codex;
- afirmações de que Codex CLI, IDE, cloud, API ou outros agents expõem ferramentas de tarefas do Codex Desktop.

Consulte [Privacidade e fluxo de dados](docs/privacy-and-data-flow.md), [Política de roteamento](docs/routing-policy.md) e [Compatibilidade](docs/compatibility.md).

## Mapa do repositório

| Caminho | Finalidade |
|---|---|
| `.codex-plugin/plugin.json` | Manifesto do plugin |
| `.agents/plugins/marketplace.json` | Entrada do marketplace |
| `skills/auto-route-for-codex/` | Skill, schemas, leitor delimitado da configuração atual, roteador, reducer de transferência respaldado por reservas e testes |
| `docs/` | Documentação em inglês, fonte de referência |
| `docs/i18n/zh-CN/` | Traduções completas para chinês simplificado |
| `scripts/verify_public_repo.py` | Verificações de repositório, tradução, privacidade e links |
| `scripts/build_release.py` | Gerador determinístico do ZIP do plugin e de `SHA256SUMS` |

## Verificação a partir de um clone limpo

```sh
python3 -m pip install --disable-pip-version-check --only-binary=:all: --require-hashes -r .github/requirements-ci.txt
python3 scripts/verify_public_repo.py --require-git-history
python3 -m unittest discover -s skills/auto-route-for-codex/tests -v
python3 skills/auto-route-for-codex/scripts/validate_contracts.py
python3 scripts/build_release.py --output-dir dist
```

A aprovação das verificações locais valida o contrato do repositório. Ela não comprova que todas as versões do host Codex oferecem a mesma interface de plugin ou de modelo; consulte [Compatibilidade](docs/compatibility.md).

## Documentação

- [Arquitetura](docs/architecture.md)
- [Instalação e reversão](docs/installation.md)
- [Contrato de configuração](docs/configuration.md)
- [Privacidade e fluxo de dados](docs/privacy-and-data-flow.md)
- [Política de roteamento](docs/routing-policy.md)
- [Compatibilidade](docs/compatibility.md)
- [Solução de problemas](docs/troubleshooting.md)
- [Perguntas frequentes](docs/faq.md)

## Status do projeto

`v0.5.0-alpha.2` reforça a privacidade do histórico público, a integridade das dependências de CI e a proveniência das versões. O contrato de roteamento em runtime não foi alterado. Consulte [CHANGELOG.md](CHANGELOG.md) e [ROADMAP.md](ROADMAP.md).

## Contribuições e segurança

Leia [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir um pull request. Relate problemas de segurança por meio do recurso privado de relato de vulnerabilidades do GitHub, conforme descrito em [SECURITY.md](SECURITY.md); não publique relatos confidenciais em uma issue pública.

## Licença

Apache License 2.0. Consulte [LICENSE](LICENSE) e [NOTICE](NOTICE).
