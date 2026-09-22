# FinGuard — Assistente Inteligente de Análise de Reclamações

Sistema para o desafio **Future Minds 3** (Zup/Itaú). Lê reclamações de clientes em texto
livre a partir de um CSV e devolve uma análise estruturada — sem precisar de chave de API para
testar (modo `mock`).

Análise completa do edital em [`analise_desafio.md`](analise_desafio.md) e a política interna
usada como base do RAG em [`ks_politica_interna.md`](ks_politica_interna.md).

## O que o sistema faz

### Entrada

Um arquivo CSV com uma reclamação por linha, com as colunas:

```
id, data_reclamacao, canal, texto_reclamacao, produto, status
```

- `canal` — de onde veio a reclamação (SAC, Ouvidoria, Banco Central, Procon, Redes Sociais...).
- `texto_reclamacao` — o relato do cliente em linguagem livre.
- `produto` — opcional; se vazio, o sistema tenta inferir pelo texto.

Hoje existem dois CSVs no repositório:

| Arquivo | Linhas | Uso |
|---|---:|---|
| `data/reclamacoes.csv` | 10 (fictícias) | teste rápido do pipeline, sem custo |
| `data/dataset_finguard_desafio_3.csv` | 500 (oficial) | dataset do desafio, usado nos benchmarks |

### Regras aplicadas

1. **Agente 1 — Estruturação** (`src/agents/estruturacao.py`): lê o texto da reclamação, busca
   trechos relevantes da política interna (`ks_politica_interna.md`) por palavra-chave, e classifica
   a reclamação em:
   - **Categoria** (Cobrança Indevida, Atendimento, Fraude/Segurança, Produto/Serviço, Cancelamento, Outros)
   - **Produto** (Cartão de Crédito, Conta Corrente, Empréstimo, Investimentos, Seguros, Não Identificado)
   - **Sentimento** (Positivo, Neutro, Negativo, Crítico)
   - **Urgência** (Baixa, Média, Alta, Crítica)
   - **Resumo** de 2-3 linhas, com palavrões e dados pessoais (CPF, telefone, cartão) automaticamente
     mascarados (`src/shared/ofuscacao.py`).

2. **Roteamento condicional** (só no nível 2, `src/application/graph.py`): a política interna
   (seção 4.3) já determina que reclamações vindas do canal **Banco Central** ou **Procon** são
   automaticamente críticas. Nesses casos o grafo pula a chamada de LLM e usa uma regra
   determinística e sem custo (`risco.executar_expresso`). Nos demais canais, chama o LLM para
   uma avaliação completa (`risco.executar_completo`).

3. **Agente 2 — Risco e Conformidade** (`src/agents/risco.py`): avalia indícios de fraude,
   violação regulatória (LGPD), risco reputacional e necessidade de escalação imediata, gerando um
   **Nível de Risco** (Baixo, Médio, Alto, Crítico) com justificativa citando a regra da política
   interna aplicada.

4. **Agente 3 — Consolidação** (`src/agents/consolidacao.py`): junta a análise do Agente 1 com o
   parecer do Agente 2 em um registro final por reclamação.

Toda chamada de agente é registrada (entrada, saída, duração) em `reports/logs.jsonl`, para
rastreabilidade de qual reclamação passou por qual agente.

### Saída

- **Nível 1** (só classificador): um registro por reclamação com categoria/produto/sentimento/
  urgência/resumo, exportado em JSON, CSV e um HTML com gráficos de distribuição.
- **Nível 2** (orquestrador completo): o mesmo registro do nível 1 + o parecer de risco, e — depois
  de processar o lote inteiro — um **relatório gerencial** (dashboard) com: distribuição por
  categoria/produto/urgência/sentimento/risco, lista das reclamações críticas/de alto risco, e
  recomendações automáticas (ex.: "70% das reclamações envolvem fraude — reforçar equipe X"). Nunca
  inclui dados pessoais do cliente.

## Status

Esqueleto funcional, testado ponta a ponta com o provider `mock` (heurísticas locais, sem custo
e sem chave de API) e já validado com o provider `anthropic` (Claude Haiku) contra o dataset
oficial — ver [`EVOLUTION.md`](EVOLUTION.md) para o histórico de benchmarks.

**Pendências conhecidas:** ver a seção [Limitações conhecidas](#limitações-conhecidas--próximos-passos)
no final deste documento.

## Arquitetura

```
CSV (pandas) ──▶ Agente 1 (estruturação) ──▶ [rotear por canal] ──▶ Agente 2 (risco) ──▶ Agente 3 (consolidação)
                       │                         │  Banco Central/Procon → risco expresso (regra, sem LLM)
                       │                         └  demais canais       → risco completo (LLM)
                       ▼
                RAG sobre a política interna (chunks por seção + busca por palavra-chave)
```

- **Nível 1** (`--nivel 1`): só o Agente 1 roda, sobre cada linha do CSV. Saída: JSON/CSV por
  reclamação + HTML com gráficos de distribuição.
- **Nível 2** (`--nivel 2`): grafo LangGraph completo (`start → agente_1 → [condicional] →
  agente_2 → agente_3 → end`). Depois de todas as reclamações passarem pelo grafo, um passo
  separado consolida o lote inteiro em um dashboard — um relatório gerencial não faz sentido por
  reclamação isolada, só faz sentido sobre o total processado.

## Estrutura de arquivos

```
FinGuard_desafio/
├── analise_desafio.md         # leitura do edital
├── ks_politica_interna.md     # política interna (fonte do RAG)
├── EVOLUTION.md               # histórico de benchmarks
├── data/
│   ├── reclamacoes.csv               # amostra de 10 linhas fictícias
│   ├── dataset_finguard_desafio_3.csv # dataset oficial (500 linhas)
│   └── gold/labels-ai-draft-v2.csv   # labels de referência p/ benchmark
├── assets/
│   ├── pack.yaml               # manifesto: versão + caminhos dos prompts/política/gold
│   └── prompts/*.json          # prompts versionados dos agentes 1 e 2
├── main.py                     # CLI (--nivel 1 | 2, --benchmark)
├── Makefile                    # comandos prontos via Docker (ver "Como rodar")
├── Dockerfile / docker-compose.yml
├── requirements.txt
├── .env.example
└── src/
    ├── domain/                 # enums (Categoria, Urgência...) e modelos pydantic
    ├── application/
    │   ├── pipeline.py         # monta o contexto e roda nível 1 / nível 2
    │   └── graph.py            # StateGraph do LangGraph + roteamento condicional
    ├── agents/
    │   ├── base.py             # agente genérico: prompt + LLM + contexto RAG
    │   ├── estruturacao.py     # Agente 1
    │   ├── risco.py            # Agente 2 — executar_completo (LLM) e executar_expresso (regra)
    │   └── consolidacao.py     # Agente 3
    ├── infrastructure/
    │   ├── data/csv_loader.py       # leitura do CSV de reclamações
    │   ├── llm/client.py            # gateway mock | anthropic | bedrock
    │   ├── llm/mock.py              # heurísticas locais (dev/teste, sem custo)
    │   ├── logging/agent_logger.py  # grava reports/logs.jsonl
    │   └── rag/politica.py          # chunking + retrieval sobre a política interna
    ├── shared/ofuscacao.py     # mascara palavrão e PII no resumo
    ├── reporting/relatorio.py  # dashboard + exportadores (json/csv/html/markdown)
    ├── prompts/loader.py       # carrega assets/pack.yaml, versiona e faz hash dos prompts
    └── benchmark/              # runner rastreável (--benchmark) + comparação com gold
└── reports/                    # saídas geradas (gitignored, exceto .gitkeep)
```

> **Nota:** os arquivos `src/graph.py`, `src/llm_client.py`, `src/mock_llm.py`, `src/relatorio.py`,
> `src/ofuscacao.py`, `src/rag.py`, `src/logging_utils.py`, `src/schemas.py` e
> `src/agents/agente1_estruturacao.py` / `agente2_risco.py` / `agente3_consolidacao.py` ainda
> existem no repositório, mas são **código legado de uma reorganização anterior** — nada no
> projeto os importa mais (o `main.py` atual usa apenas os módulos em `src/application`,
> `src/infrastructure`, `src/domain`, `src/reporting` e `src/shared` listados acima). Podem ser
> removidos com segurança em uma limpeza futura.

## Como rodar

Existem duas formas de rodar o projeto. **Se você nunca configurou Python neste computador,
use a Opção 1 (Docker) — é a mais simples.**

### Opção 1 — Docker + Makefile (recomendado, sem instalar Python)

**Pré-requisitos:** ter o [Docker Desktop](https://www.docker.com/products/docker-desktop/)
instalado e aberto. Nada mais precisa ser instalado — o `Dockerfile` já cuida do Python e das
dependências.

**Passo a passo:**

```bash
# 1. entrar na pasta do projeto
cd FinGuard_desafio

# 2. criar o arquivo de configuração (o padrão já funciona sem chave de API)
cp .env.example .env

# 3. construir a imagem Docker (só precisa fazer isso uma vez, ou quando o código mudar)
make build

# 4. rodar o nível 1 (classificador) sobre a amostra de 10 reclamações
make run-nivel1

# 5. rodar o nível 2 (orquestrador completo, com relatório gerencial)
make run-nivel2
```

Os resultados aparecem na pasta `reports/` (ver [Como ver os resultados](#como-ver-os-resultados)).

**Todos os comandos disponíveis** (rode `make help` para ver esta lista no terminal):

| Comando | O que faz |
|---|---|
| `make build` | Constrói a imagem Docker (necessário antes do primeiro `make run-*`) |
| `make rebuild` | Reconstrói a imagem do zero, sem cache (use se algo parecer "preso") |
| `make run` | Alias de `make run-nivel1` |
| `make run-nivel1` | Roda o nível 1 (só o classificador) sobre `data/reclamacoes.csv` |
| `make run-nivel2` | Roda o nível 2 (orquestrador completo + relatório gerencial) |
| `make run-nivel1-limit LIMIT=5` | Roda o nível 1 só nas primeiras 5 linhas (padrão: 5 se omitido) |
| `make run-nivel2-limit LIMIT=5` | Roda o nível 2 só nas primeiras 5 linhas (padrão: 5 se omitido) |
| `make benchmark-nivel1` | Roda o nível 1 em modo benchmark, comparando com o gold em `data/gold/` |
| `make benchmark-nivel2` | Roda o nível 2 em modo benchmark, comparando com o gold em `data/gold/` |
| `make shell` | Abre um terminal interativo dentro do container (debug) |
| `make clean-reports` | Apaga os arquivos gerados em `reports/` (json/csv/html/md/jsonl) |

**Variáveis opcionais** — combine com qualquer comando `make run-*` ou `make benchmark-*`
escrevendo `VARIAVEL=valor` depois do comando:

| Variável | Para quê serve | Exemplo |
|---|---|---|
| `INPUT` | trocar o CSV de entrada (padrão: `data/reclamacoes.csv`) | `make run-nivel2 INPUT=data/dataset_finguard_desafio_3.csv` |
| `LIMIT` | processar só as N primeiras linhas | `make run-nivel1 LIMIT=20` |
| `PROVIDER` | trocar o provider de LLM (`mock`, `anthropic`, `bedrock`) | `make run-nivel1 PROVIDER=anthropic` |
| `MODEL` | forçar um model id específico do provider | `make run-nivel1 PROVIDER=anthropic MODEL=claude-haiku-4-5` |
| `GOLD` | trocar o CSV gold usado no benchmark (padrão: `data/gold/labels-ai-draft-v2.csv`) | `make benchmark-nivel1 GOLD=data/gold/outro.csv` |
| `ARGS` | passar qualquer flag extra do `main.py` direto | `make run-nivel1 ARGS="--pack assets/pack.yaml"` |

Exemplo combinando variáveis — rodar as 100 primeiras reclamações do dataset oficial, nível 2,
usando Anthropic:

```bash
make run-nivel2 INPUT=data/dataset_finguard_desafio_3.csv LIMIT=100 PROVIDER=anthropic
```

> Se você quiser usar o provider `anthropic` ou `bedrock` (em vez do `mock`), edite o `.env`
> antes do passo 4 e preencha `ANTHROPIC_API_KEY` (ou as credenciais AWS padrão do `boto3`, no
> caso do `bedrock`) — ver [Providers de LLM](#providers-de-llm).

### Opção 2 — Python local, sem Docker

Use esta opção só se já tiver Python 3.12+ instalado e preferir rodar fora de um container.

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # ajuste o provider/chave se necessário

# Nível 1 — classificador, sobre o dataset de amostra
python main.py --nivel 1 --input data/reclamacoes.csv

# Nível 2 — orquestrador multi-agente com relatório gerencial
python main.py --nivel 2 --input data/reclamacoes.csv

# Teste rápido só com as 5 primeiras linhas
python main.py --nivel 2 --limit 5

# Forçar um provider específico sem editar o .env
python main.py --nivel 2 --provider anthropic

# Rodar como benchmark rastreável, comparando com o gold
python main.py --nivel 1 --input data/dataset_finguard_desafio_3.csv --limit 100 --benchmark
```

## Como ver os resultados

```bash
# abrir o relatório no navegador padrão
xdg-open reports/relatorio_nivel1.html        # nível 1
xdg-open reports/relatorio_gerencial.html     # nível 2

# no WSL, se não tiver ambiente gráfico configurado:
explorer.exe reports/relatorio_gerencial.html

# ou só ler no terminal
cat reports/relatorio_gerencial.md
cat reports/resultados_nivel2.json
cat reports/logs.jsonl   # log de execução por agente (entrada/saída/duração)
```

No Windows (fora do WSL), basta abrir a pasta `reports/` no Explorer e dar duplo-clique no
arquivo `.html`.

Saídas em `reports/`:
- `resultados_nivel{1,2}.json` / `.csv` — um registro por reclamação
- `relatorio_nivel1.html` — gráficos de distribuição (categoria/produto/urgência/sentimento)
- `relatorio_gerencial.html` / `.md` — dashboard + reclamações críticas + recomendações (nível 2)
- `logs.jsonl` — uma linha por chamada de agente (`reclamacao_id`, `agente`, `entrada`, `saida`,
  `duracao_ms`), para rastreabilidade
- `benchmarks/<run_id>/` — quando rodado com `--benchmark`: metadados do run, execuções amostradas
  e (se houver gold) a análise de concordância

## Providers de LLM

| Provider | Requer | Uso |
|---|---|---|
| `mock` | nada | heurísticas por palavra-chave, sem custo — desenvolvimento/demo offline |
| `anthropic` | `ANTHROPIC_API_KEY` | API da Anthropic, saída estruturada via tool-calling forçado |
| `bedrock` | credenciais AWS (boto3) | Amazon Bedrock, API `converse` com `toolConfig` |
| `litellm` | `LITELLM_TOKEN` (+ `LITELLM_BASE_URL`) | AI Gateway (LiteLLM) do desafio Future Minds, SDK `openai` com tool-calling forçado |

Todos implementam a mesma interface (`LLMGateway.gerar_estruturado(system, user, schema)`), então
trocar de provider é só variável de ambiente (ou `--provider` na CLI) — nenhum código de agente muda.

## Mapeamento com os requisitos do desafio

| Requisito do edital | Onde está |
|---|---|
| Categoria / Produto / Sentimento / Urgência / Resumo | `src/domain/models.py` (`AnaliseEstruturada`), `src/agents/estruturacao.py` |
| RAG sobre a política interna | `src/infrastructure/rag/politica.py` (chunking por seção + retrieval por palavra-chave) |
| Palavras impróprias ofuscadas no resumo | `src/shared/ofuscacao.py`, aplicado em `src/agents/estruturacao.py` |
| `.html` com gráfico + `.json`/`.csv` por reclamação | `src/reporting/relatorio.py`, chamado em `main.py` |
| Multi-agente orquestrado (LangGraph) | `src/application/graph.py` |
| Análise de Risco e Conformidade (fraude, LGPD, reputacional, escalação) | `src/domain/models.py` (`ParecerRisco`), `src/agents/risco.py` |
| Relatório gerencial (dashboard, críticas, recomendações) | `src/reporting/relatorio.py` (`montar_dashboard` + `exportar_markdown/html`) |
| Fluxo condicional | roteamento `risco_expresso` vs `risco_completo` em `src/application/graph.py` |
| Logs de execução (entrada/saída/tempo por agente) | `src/infrastructure/logging/agent_logger.py` → `reports/logs.jsonl` |
| Rastreabilidade (em qual agente a reclamação está) | campo `agente` em cada linha de `logs.jsonl` |
| Sem persistência em nuvem | tudo grava em `reports/` local; nenhuma chamada a S3/afins |
| Otimização de custo (bônus) | caminho `risco_expresso` sem LLM quando a política já decide por regra |
| Nenhum dado pessoal em relatório gerencial | `src/shared/ofuscacao.py` (`mascarar_dados_pessoais`: CPF/telefone/cartão) |
| Benchmark rastreável com hashes e prompts versionados (bônus) | `src/benchmark/`, `assets/pack.yaml`, ver [`EVOLUTION.md`](EVOLUTION.md) |

## Limitações conhecidas / próximos passos

- **Dataset real**: `data/dataset_finguard_desafio_3.csv` já é o CSV oficial do desafio
  (~500 reclamações) e é o recomendado para benchmark. `data/reclamacoes.csv` continua sendo só
  uma amostra fictícia de 10 linhas, útil para testar o pipeline rapidamente sem custo. O código
  já lê qualquer CSV com as colunas `id, data_reclamacao, canal, texto_reclamacao, produto, status`.
- **Provider `mock`**: é heurística por palavra-chave, não um LLM. Serve para validar o pipeline
  sem custo, mas a qualidade real da classificação só se avalia com `anthropic` ou `bedrock`
  configurado (ver benchmark validado em [`EVOLUTION.md`](EVOLUTION.md): categoria 70%, produto
  85%, urgência 78% com Claude Haiku sobre 100 amostras do dataset oficial).
- **RAG**: retrieval por sobreposição de palavras-chave, adequado para um documento único e curto.
  Se a política crescer muito, vale evoluir para embeddings (`sentence-transformers` + busca por
  similaridade), sem precisar reescrever a interface (`PoliticaRAG.buscar_contexto`).
- **Paralelismo**: hoje o loop sobre as reclamações é sequencial. Dá para paralelizar (ex.:
  `concurrent.futures` ou `app.batch` do LangGraph) sem mudar a lógica dos agentes.
- **Provider `bedrock`**: implementado contra a API `converse`, mas ainda não testado contra uma
  conta AWS real — validar antes da apresentação se for o caminho escolhido.
- **Código legado**: os módulos antigos listados na nota da seção
  [Estrutura de arquivos](#estrutura-de-arquivos) não são mais usados por nenhum código ativo e
  podem ser removidos numa limpeza futura.
