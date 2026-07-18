---
translation_of: README.md
source_revision: docs-v0.4.0-alpha.1
last_synced_version: 0.4.0-alpha.1
---

# Auto Route for Codex

**Idioma:** [English](README.md) | Português (Brasil) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Türkçe](README.tr.md) | [Русский](README.ru.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Deutsch](README.de.md) | [Español](README.es.md)

> Projeto comunitário em fase alfa. Não é um produto oficial da OpenAI.

Auto Route for Codex é um plugin do Codex com ativação explícita que recomenda uma função de modelo, um nível de esforço de raciocínio e uma topologia de execução suficientes a partir de um perfil de tarefa com limites de privacidade. A edição pública foi deliberadamente projetada para apenas fazer recomendações: ela nunca bifurca, cria, navega, arquiva ou repete uma tarefa.

## Por que este projeto existe

A escolha do modelo e o esforço de raciocínio são decisões distintas. Uma tarefa curta, porém arriscada, pode exigir um modelo mais forte, enquanto um trabalho longo, repetitivo e verificável pode se beneficiar de um modelo mais rápido. Este plugin torna essas escolhas explícitas sem transformar a seleção do modelo em um efeito colateral invisível.

O contrato público segue quatro regras:

- a ativação é explícita por meio de `$auto-route-for-codex`;
- somente os campos enumerados do perfil chegam ao roteador determinístico;
- uma recomendação é resolvida somente com base nos valores de modelo e de thinking fornecidos pelo host;
- toda decisão pública permanece `stay + none|efficiency + none + keep`.

## Início rápido

Pré-requisitos:

- uma interface do Codex que ofereça suporte a plugins e à invocação explícita de skills;
- a Codex CLI disponível no `PATH`;
- acesso ao repositório Git público.

```sh
codex plugin marketplace add jacob101519/auto-route-for-codex --ref v0.4.0-alpha.1
codex plugin add auto-route-for-codex@jacob101519
```

Inicie uma nova tarefa do Codex, selecione **Auto Route for Codex** ou invoque:

```text
$auto-route-for-codex Review this task and recommend a sufficient Codex setting.
```

O plugin retorna uma recomendação versionada. Ele não altera o modelo nem as configurações da tarefa atual.

## Limite de segurança da edição pública

Incluído:

- schemas JSON rigorosos de entrada e saída;
- lógica de roteamento determinística;
- testes que apenas fazem recomendações e casos semânticos negativos;
- scripts de verificação do repositório público e do release;
- documentação em inglês e tradução completa para chinês simplificado.

Excluído intencionalmente:

- leitores locais de arquivos de sessão;
- recibos ou catálogos privados da configuração atual;
- orquestração de bifurcação, navegação, arquivamento e repetição de tarefas;
- logs de execução, credenciais, caminhos locais, identificadores de tarefas ou configurações privadas;
- alterações automáticas de modelo ou gravações na configuração global do Codex.

Consulte [Privacidade e fluxo de dados](docs/privacy-and-data-flow.md) e [Política de roteamento](docs/routing-policy.md).

## Mapa do repositório

| Caminho | Finalidade |
|---|---|
| `.codex-plugin/plugin.json` | Manifesto do plugin |
| `.agents/plugins/marketplace.json` | Entrada do marketplace |
| `skills/auto-route-for-codex/` | Skill, schemas, roteador e testes |
| `docs/` | Documentação em inglês, fonte de referência |
| `docs/i18n/zh-CN/` | Traduções completas para chinês simplificado |
| `scripts/verify_public_repo.py` | Verificações de repositório, tradução, privacidade e links |
| `scripts/build_release.py` | Gerador determinístico do ZIP do plugin e de `SHA256SUMS` |

## Verificação a partir de um clone limpo

```sh
python3 scripts/verify_public_repo.py
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

`v0.4.0-alpha.1` é a primeira versão alfa pública. A API e a estrutura do pacote podem mudar antes de uma versão estável. Consulte [CHANGELOG.md](CHANGELOG.md) e [ROADMAP.md](ROADMAP.md).

## Contribuições e segurança

Leia [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir um pull request. Relate problemas de segurança por meio do recurso privado de relato de vulnerabilidades do GitHub, conforme descrito em [SECURITY.md](SECURITY.md); não publique relatos confidenciais em uma issue pública.

## Licença

Apache License 2.0. Consulte [LICENSE](LICENSE) e [NOTICE](NOTICE).
