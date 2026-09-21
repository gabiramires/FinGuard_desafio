# FinGuard — Assistente Inteligente de Análise de Reclamações

Sistema para o desafio **Future Minds 3** (Zup/Itaú). Recebe reclamações de clientes em texto
livre e devolve uma análise estruturada (categoria, produto, sentimento, urgência, resumo) e,
no modo orquestrado, um parecer de risco/conformidade e um relatório gerencial agregado.

Análise completa do edital em [`analise_desafio.md`](analise_desafio.md) e a política interna
usada como base do RAG em [`ks_politica_interna.md`](ks_politica_interna.md).

## Status

Esqueleto funcional, testado ponta a ponta com o provider `mock` (heurísticas locais, sem custo
e sem chave de API). **Ainda falta**: (1) o CSV oficial do dataset (~500 reclamações — hoje há
só uma amostra de 10 linhas fictícias em `data/reclamacoes.csv` para permitir testar o
pipeline); (2) plugar um provider real (`anthropic` ou `bedrock`) para a classificação de
verdade — o mock existe só para desenvolvimento/demonstração offline, não deve ser usado para
avaliar a qualidade da classificação.

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
  separado (`relatorio.py`) consolida o lote inteiro em um dashboard — um relatório gerencial
  não faz sentido por reclamação isolada, só faz sentido sobre o total processado.

### Por que o roteamento condicional depois do Agente 1?

A política interna (seção 4.3) já determina, por regra, que reclamações de canal **Banco
Central** ou **Procon** são automaticamente críticas. Nesses casos o grafo pula a chamada de
LLM do Agente 2 e usa `agente2_risco.executar_expresso` (regra determinística, custo zero). Nos
demais canais, roda `executar_completo` (LLM avalia fraude, LGPD, risco reputacional). Isso
implementa ao mesmo tempo o fluxo condicional sugerido no edital e o critério bônus de
otimização de custo.

## Estrutura de arquivos

```
FinGuard_desafio/
├── analise_desafio.md         # leitura do edital
├── ks_politica_interna.md     # política interna (fonte do RAG)
├── data/reclamacoes.csv       # dataset (hoje: amostra de 10 linhas fictícias)
├── main.py                    # CLI (--nivel 1 | 2)
├── requirements.txt
├── .env.example
└── src/
    ├── schemas.py             # AnaliseEstruturada, ParecerRisco, RegistroReclamacao (pydantic)
    ├── rag.py                 # chunking + retrieval sobre a política interna
    ├── ofuscacao.py           # mascara palavrão e PII no resumo
    ├── llm_client.py          # wrapper mock | anthropic | bedrock, saída estruturada via tool-calling
    ├── mock_llm.py            # heurísticas locais (dev/teste, sem custo)
    ├── logging_utils.py       # AgentLogger → reports/logs.jsonl
    ├── graph.py                # StateGraph do LangGraph (nível 2)
    ├── relatorio.py            # dashboard + exportadores (json/csv/html/markdown)
    └── agents/
        ├── agente1_estruturacao.py
        ├── agente2_risco.py     # executar_completo (LLM) e executar_expresso (regra)
        └── agente3_consolidacao.py
└── reports/                    # saídas geradas (gitignored, exceto .gitkeep)
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ajuste o provider/chave
```

`.env`:
```
FINGUARD_LLM_PROVIDER=mock     # mock | anthropic | bedrock
ANTHROPIC_API_KEY=             # se provider=anthropic
AWS_REGION=us-east-1           # se provider=bedrock (usa credenciais padrão do boto3)
```

## Como rodar

```bash
# Nível 1 — classificador, sobre o dataset de amostra
python main.py --nivel 1 --input data/reclamacoes.csv

# Nível 2 — orquestrador multi-agente com relatório gerencial
python main.py --nivel 2 --input data/reclamacoes.csv

# Teste rápido só com as 5 primeiras linhas
python main.py --nivel 2 --limit 5

# Forçar um provider específico sem editar o .env
python main.py --nivel 2 --provider anthropic
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

Saídas em `reports/`:
- `resultados_nivel{1,2}.json` / `.csv` — um registro por reclamação
- `relatorio_nivel1.html` — gráficos de distribuição (categoria/produto/urgência/sentimento)
- `relatorio_gerencial.html` / `.md` — dashboard + reclamações críticas + recomendações (nível 2)
- `logs.jsonl` — uma linha por chamada de agente (`reclamacao_id`, `agente`, `entrada`, `saida`,
  `duracao_ms`), para rastreabilidade

## Providers de LLM

| Provider | Requer | Uso |
|---|---|---|
| `mock` | nada | heurísticas por palavra-chave, sem custo — desenvolvimento/demo offline |
| `anthropic` | `ANTHROPIC_API_KEY` | API da Anthropic, saída estruturada via tool-calling forçado |
| `bedrock` | credenciais AWS (boto3) | Amazon Bedrock, API `converse` com `toolConfig` |

Todos implementam a mesma interface (`LLMClient.gerar_estruturado(system, user, schema)`), então
trocar de provider é só variável de ambiente — nenhum código de agente muda.

## Mapeamento com os requisitos do desafio

| Requisito do edital | Onde está |
|---|---|
| Categoria / Produto / Sentimento / Urgência / Resumo | `schemas.AnaliseEstruturada`, `agents/agente1_estruturacao.py` |
| RAG sobre a política interna | `rag.py` (chunking por seção + retrieval por palavra-chave) |
| Palavras impróprias ofuscadas no resumo | `ofuscacao.ofuscar_palavroes`, aplicado em `agente1_estruturacao.executar` |
| `.html` com gráfico + `.json`/`.csv` por reclamação | `relatorio.exportar_html/json/csv`, chamados em `main.py` |
| Multi-agente orquestrado (LangGraph) | `graph.py` |
| Análise de Risco e Conformidade (fraude, LGPD, reputacional, escalação) | `schemas.ParecerRisco`, `agents/agente2_risco.py` |
| Relatório gerencial (dashboard, críticas, recomendações) | `relatorio.montar_dashboard` + `exportar_markdown/html` |
| Fluxo condicional | roteamento `risco_expresso` vs `risco_completo` em `graph.py` |
| Logs de execução (entrada/saída/tempo por agente) | `logging_utils.AgentLogger` → `reports/logs.jsonl` |
| Rastreabilidade (em qual agente a reclamação está) | campo `agente` em cada linha de `logs.jsonl` |
| Sem persistência em nuvem | tudo grava em `reports/` local; nenhuma chamada a S3/afins |
| Otimização de custo (bônus) | caminho `risco_expresso` sem LLM quando a política já decide por regra |
| Nenhum dado pessoal em relatório gerencial | `ofuscacao.mascarar_dados_pessoais` (CPF/telefone/cartão) |

## Limitações conhecidas / próximos passos

- **Dataset real**: falta o CSV oficial do desafio (~500 reclamações). O código já lê qualquer
  CSV com as colunas `id, data_reclamacao, canal, texto_reclamacao, produto, status` — basta
  substituir `data/reclamacoes.csv`.
- **Provider `mock`**: é heurística por palavra-chave, não um LLM. Serve para validar o
  pipeline sem custo, mas a qualidade real da classificação só se avalia com `anthropic` ou
  `bedrock` configurado. No teste com a amostra, o mock já erra categoria em casos que exigem
  mais nuance (ex.: reclamação de juros de empréstimo caiu em "Outros" em vez de
  "Produto/Serviço") — esperado, não é o classificador final.
- **RAG**: retrieval por sobreposição de palavras-chave, adequado para um documento único e
  curto. Se a política crescer muito, vale evoluir para embeddings (`sentence-transformers` +
  busca por similaridade), sem precisar reescrever a interface (`rag.buscar_contexto`).
- **Paralelismo**: hoje o loop sobre as reclamações é sequencial. Dá para paralelizar (ex.:
  `concurrent.futures` ou `app.batch` do LangGraph) sem mudar a lógica dos agentes.
- **Provider `bedrock`**: implementado contra a API `converse`, mas ainda não testado contra uma
  conta AWS real — validar antes da apresentação se for o caminho escolhido.
