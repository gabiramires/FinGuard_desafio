# Evolution benchmarks — FinGuard

Histórico técnico de benchmarks do pipeline FinGuard. **Não é dataset gold.**
Referência de comparação: `data/gold/labels-ai-draft-v2.csv` (AI draft, revisão
humana pendente — importado do inference-triage).

## Convenções

- **Nível 1**: agente de estruturação → `categoria`, `produto`, `sentimento`, `urgencia`.
- **Nível 2**: grafo completo + `nivel_risco` (ainda sem run registrado aqui).
- Concordância = match exato predição vs label gold (exploratório).
- Join por `sample_id`; integridade via `source_text_hash` (`canonical-text-v1`).
- Metadados por run: `reports/benchmarks/<run_id>/benchmark_run.json`.

### `LIMIT` vs tamanho do CSV

```text
amostras_processadas = min(LIMIT, linhas_do_CSV)
```

| Comando | Resultado |
|---|---|
| `LIMIT=100` + `data/reclamacoes.csv` (10 linhas) | **10** processadas |
| `LIMIT=100` + `data/dataset_finguard_desafio_3.csv` (500 linhas) | **100** processadas |

## Datasets

| Arquivo | Linhas | sha256 |
|---|---:|---|
| `data/reclamacoes.csv` | 10 | `435c5e57…2917c3` |
| `data/dataset_finguard_desafio_3.csv` | 500 | `9eeee122…4cfe37` |
| `data/gold/labels-ai-draft-v2.csv` | 500 | `3f7b82c4…7e3ed` |

**Importante:** a amostra de 10 linhas compartilha IDs com o gold, mas textos
diferentes → `hash_mismatches` em 100% das comparações. **Não usar para medir
qualidade.** Usar sempre o dataset oficial para benchmark vs gold.

## Assets versionados

```text
pack:          finguard-pack-v1
prompt (ag.1): agente1-estruturacao-v1
prompt (ag.2): agente2-risco-v1
pack_hash:     e029b3d2f3b83f921b97ec697fee54b676c7da2c93c4d2f76c9e15c317814fac
prompt_hash:   2f995e9cb19d1e41acb7833a2c99020bb68c2ebdbbb5f0197c069e3593119e96
```

## Runs coletados

| Run ID | Provider | Model | INPUT | LIMIT | Proc. | Hash OK | Status |
|---|---|---|---|---:|---:|---:|---|
| `4ee43002-…` | anthropic | claude-haiku-4-5 | amostra 10 | 100 | 10 | 0/10 | completed* |
| `cf7af2ff-…` | anthropic | claude-haiku-4-5 | **oficial 500** | 100 | **100** | **100/100** | **completed** |
| `2122ba59-…` | mock | mock-heuristics-v1 | amostra 10 | 5 | 5 | 0/5 | completed* |
| `4fcbaafa-…` | mock | mock-heuristics-v1 | amostra 10 | 3 | 3 | 0/3 | completed* |

\*Run na amostra local — comparação gold inválida (textos divergentes).

---

## Run principal — Haiku 100 amostras vs gold

```text
run_id:        cf7af2ff-3960-4464-91fa-f148845bd2b0
início:        2026-09-22T14:38:59Z
duração:       206,4s (~2,1 min)
provider:      anthropic
model:         claude-haiku-4-5
prompt:        agente1-estruturacao-v1
input:         data/dataset_finguard_desafio_3.csv
limit:         100
config_hash:   9e942a7a6e04bf1fbdda3d7d01d961c49d8aafebe5fa796afaf1909288038c98
```

Comando reproduzível:

```bash
make benchmark-nivel1 \
  INPUT=data/dataset_finguard_desafio_3.csv \
  LIMIT=100
```

### Cobertura e integridade

| Métrica | Valor |
|---|---:|
| Labels no gold | 500 |
| Predictions | 100 |
| IDs matched | 100 |
| IDs extras | 0 |
| **Hash mismatches** | **0** |
| Status | completed |

### Concordância vs `labels-ai-draft-v2` (100 amostras)

| Campo | Acertos | Taxa |
|---|---:|---:|
| **Categoria** | 70/100 | **70,0%** |
| **Produto** | 85/100 | **85,0%** |
| Sentimento | 51/100 | 51,0% |
| **Urgência** | 78/100 | **78,0%** |

Referência inference-triage (Laya local, 500 amostras, mesmo gold draft):

| Campo | Laya local (500) | Haiku v1 (100) |
|---|---:|---:|
| Categoria | 45,8% | **70,0%** |
| Produto | 78,2% | **85,0%** |
| Urgência | 71,8% | **78,0%** |

> Comparação direta é indicativa (tamanhos de amostra diferentes), mas Haiku v1
> neste subset já supera Laya em categoria e produto.

### Principais confusões de categoria (gold → pred)

| Gold | Predito | Count |
|---|---|---:|
| Outros | Fraude/Segurança | 10 |
| Fraude/Segurança | Cobrança Indevida | 7 |
| Cancelamento | Cobrança Indevida | 4 |
| Produto/Serviço | Atendimento | 4 |
| Cobrança Indevida | Produto/Serviço | 2 |

Padrão: o modelo tende a **elevar severidade** (Outros→Fraude) ou agrupar em
Cobrança Indevida quando o gold usa categorias mais específicas.

### Performance (agente 1, Haiku)

| Métrica | Valor |
|---|---:|
| Média | 2.063 ms |
| P50 | 2.016 ms |
| P95 | 2.753 ms |
| Máximo | 3.037 ms |
| Total 100 amostras | ~206 s |

Custo estimado (Haiku 4.5: ~$1/$5 por MTok in/out — ordem de grandeza):

```text
~100 chamadas × ~1,5k tokens ≈ benchmark exploratório de centavos, não dólares
```

---

## Run inválido — amostra local (referência do bug LIMIT)

Run `4ee43002` — `LIMIT=100` na amostra de 10 linhas:

| Métrica | Valor |
|---|---:|
| Processadas | 10 (não 100) |
| Hash mismatches | 10/10 |
| Categoria | 0% |
| Produto | 10% |

**Causa:** `data/reclamacoes.csv` tem textos diferentes do source do gold.
**Lição:** sempre `INPUT=data/dataset_finguard_desafio_3.csv` para comparação gold.

---

## Gates — run `cf7af2ff`

| Gate | Critério | Resultado | Status |
|---|---|---:|---|
| Run completou | status=completed | sim | PASS |
| Dataset oficial | hash `9eee…cfe37` | sim | PASS |
| Hash mismatches | 0 | 0 | PASS |
| Categoria ≥ 45% | exploratório | 70,0% | **PASS** |
| Produto ≥ 76% | exploratório | 85,0% | **PASS** |
| Urgência ≥ 70% | exploratório | 78,0% | **PASS** |
| Sentimento ≥ 50% | exploratório | 51,0% | PASS |

Próximo gate sugerido: rodar **500 amostras** completas e verificar estabilidade.

---

## Estado da evolução

### Concluído

- arquitetura em camadas + prompts versionados + benchmark rastreável;
- primeiro benchmark **válido** Haiku vs gold (100 amostras, 0 hash mismatches);
- categoria 70%, produto 85%, urgência 78% no subset.

### Próximos passos

1. Benchmark full 500: `make benchmark-nivel1 INPUT=data/dataset_finguard_desafio_3.csv`
2. Nível 2 com concordância de `risk`: `make benchmark-nivel2 …`
3. Prompt v2 focado em: Outros↔Fraude, Cancelamento↔Cobrança, calibragem de sentimento
4. Registrar latência agregada no runner (p50/p95 automáticos)
5. Gate de sentimento ≥ 60% antes de promover prompt

## Ciclo de melhoria

```text
execução (--benchmark + INPUT oficial)
  → sample_executions.jsonl
  → benchmark_analysis.json vs gold
  → EVOLUTION.md (este arquivo)
  → ajuste prompt/model
  → novo config_hash / prompt_hash
```

## Referências

- [Run Haiku 100 — metadata](reports/benchmarks/cf7af2ff-3960-4464-91fa-f148845bd2b0/benchmark_run.json)
- [Análise vs gold](reports/benchmarks/cf7af2ff-3960-4464-91fa-f148845bd2b0/benchmark_analysis.json)
- [Execuções](reports/benchmarks/cf7af2ff-3960-4464-91fa-f148845bd2b0/sample_executions.jsonl)
- [Logs agente 1](reports/benchmarks/cf7af2ff-3960-4464-91fa-f148845bd2b0/logs.jsonl)
- [Gold labels](data/gold/labels-ai-draft-v2.csv)
