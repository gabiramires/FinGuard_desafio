# Avaliação de arquitetura — projeção de custo

> Documento gerado em 22/09/2026. Projeta custo operacional das composições possíveis para o
> FinGuard, usando o dataset oficial e a arquitetura atual do `FinGuard_desafio`.

## 1. Escopo e premissas

### Dataset de referência

```text
Arquivo:  data/dataset_finguard_desafio_3.csv
Registros: 500
Canais:   SAC 133 | Ouvidoria 127 | Banco Central 121 | Redes Sociais 119
Produto vazio: 122 registros (24,4%)
```

### Arquitetura atual (`FinGuard_desafio`)

```text
Por reclamação:
  Agente 1 (LLM + RAG)     → sempre
  Agente 2 (LLM ou regra)  → 75,8% LLM | 24,2% regra expressa
  Agente 3 (local)         → sempre, sem LLM
Pós-lote:
  relatorio.py             → local, sem LLM
```

A rota expressa (`executar_expresso`) dispara quando o canal é **Banco Central** ou **Procon**.
No dataset oficial, só **Banco Central** aparece (121 casos = 24,2%). Procon existe na amostra
fictícia (`data/reclamacoes.csv`), mas não no CSV oficial.

### Hipóteses de tokens por chamada LLM

Estimativas conservadoras para reclamações em português, incluindo system prompt, contexto RAG e
saída estruturada via tool-calling:

| Chamada | Tokens entrada | Tokens saída | Observação |
|---|---:|---:|---|
| Agente 1 (estruturação) | ~1.200 | ~180 | Política RAG (~400 tok) + texto (~600 tok) + instruções |
| Agente 2 (risco completo) | ~900 | ~150 | Análise estruturada + texto original resumido |
| Agente 2 (expresso) | 0 | 0 | Regra determinística |

Média por reclamação **com arquitetura atual**:

```text
Agente 1:     1.200 in + 180 out  (100% dos casos)
Agente 2 LLM:   900 in + 150 out  (75,8% dos casos)
─────────────────────────────────────────────────
Média ponderada por reclamação:
  entrada  = 1.200 + (0,758 × 900) = 1.882 tokens
  saída    = 180   + (0,758 × 150) = 294 tokens
```

Para **500 reclamações** (um lote do desafio):

```text
Entrada total:  ~941.000 tokens
Saída total:    ~147.000 tokens
```

Para **1 milhão de reclamações** (projeção operacional):

```text
Entrada total:  ~1,88 bilhão de tokens
Saída total:    ~294 milhões de tokens
```

---

## 2. Preços de referência (set/2026)

Valores públicos aproximados; atualizar antes de qualquer decisão de produção. Não incluem cache,
batch discount, impostos ou retries.

| Provider / modelo | Entrada (US$/1M tok) | Saída (US$/1M tok) | Uso sugerido |
|---|---:|---:|---|
| Claude Haiku 4.5 | 1,00 | 5,00 | Agente 1 (volume) |
| Claude Sonnet 4.5 | 3,00 | 15,00 | Agente 2 (risco) |
| Claude Sonnet (Bedrock) | ~3,00 | ~15,00 | Equivalente Anthropic |
| Kimi K2 Turbo | 1,15 | 8,00 | Alternativa custo |
| Laya local (ONNX) | 0 | 0 | Decisão estruturada |
| Mock / regras | 0 | 0 | Dev e rotas expressas |

---

## 3. Cenários de custo

### Cenário A — Arquitetura atual, um modelo para tudo (Sonnet)

Usa o mesmo modelo nos Agentes 1 e 2. Simples de operar; mais caro.

| Escala | Custo entrada | Custo saída | **Total API** |
|---|---:|---:|---:|
| 500 reclamações | US$ 5,64 | US$ 4,41 | **~US$ 10,05** |
| 1 milhão | US$ 5.640 | US$ 4.410 | **~US$ 10.050** |

Latência estimada: **3,5–8,8 s** por reclamação (2 chamadas LLM sequenciais + overhead).

### Cenário B — Arquitetura atual com rota expressa (Sonnet)

Igual ao implementado hoje. Economia de 24,2% na segunda chamada.

| Escala | **Total API** | vs Cenário C (sem rota) |
|---|---:|---|
| 500 reclamações | **~US$ 8,30** | −17% |
| 1 milhão | **~US$ 8.300** | −17% |

**Economia da rota expressa por lote de 500:** ~US$ 1,75 em API (121 chamadas de Agente 2 evitadas).

Para a banca, o argumento não é o valor absoluto (centavos por lote), mas a **proporção evitável**
quando regras de negócio já decidem o resultado.

### Cenário C — Arquitetura atual sem rota expressa (Sonnet)

Todas as reclamações passam pelo Agente 2 via LLM.

| Escala | **Total API** |
|---|---:|
| 500 reclamações | ~US$ 10,05 |
| 1 milhão | ~US$ 10.050 |

### Cenário D — Modelos tiered (Haiku no Agente 1, Sonnet no Agente 2)

Alinhado ao critério bônus do edital ("modelo menor para tarefas simples").

| Componente | Tokens (500 req) | Custo |
|---|---|---:|
| Agente 1 × 500 (Haiku) | 600k in + 90k out | ~US$ 1,05 |
| Agente 2 × 379 (Sonnet) | 341k in + 57k out | ~US$ 1,88 |
| **Total** | | **~US$ 2,93** |

| Escala | **Total API** | vs Cenário B (Sonnet único) |
|---|---:|---|
| 500 reclamações | **~US$ 2,93** | −65% |
| 1 milhão | **~US$ 5.860** | −29% |

**Recomendação para o desafio:** este é o melhor equilíbrio custo/qualidade sem mudar a arquitetura.

### Cenário E — Híbrido Laya + LLM seletivo (referência `inference-triage`)

Não é a arquitetura do edital, mas é a alternativa de menor custo para volume alto.

```text
Laya local     → categoria, produto, urgência, risco preliminar (US$ 0 API)
LLM (Haiku)    → resumo apenas nos críticos (~63% do baseline = 315/500)
```

Projeção para 1 milhão (fonte: `inference-triage/justification.md`):

| Composição | Custo API estimado (Haiku) |
|---|---:|
| Laya + resumo em todos | ~US$ 1.350 |
| Laya + resumo só nos críticos | ~US$ 851 |
| Agents LLM com rota expressa | ~US$ 2.406 |
| Agents LLM sem rota expressa | ~US$ 2.719 |

Economia híbrida vs agents: **~44–65%** em API, trocando qualidade de classificação LLM por
decisor local (~46% concordância em categoria no benchmark Laya atual).

---

## 4. Custo por componente da arquitetura

| Componente | Custo API | Custo compute | Valor para o desafio |
|---|---|---|---|
| Agente 1 (LLM estruturação) | Alto (100% das req) | Baixo | **Essencial** — núcleo do Nível 1 |
| RAG keyword | Zero | Negligível | **Justificado** — contexto da política |
| Agente 2 LLM | Médio (75,8% das req) | Baixo | **Essencial** — Nível 2 |
| Agente 2 expresso | Zero | Negligível | **Alto ROI** — manter e expandir |
| Agente 3 consolidação | Zero | Negligível | **Essencial** — empacotamento |
| `relatorio.py` + Plotly | Zero | Negligível | **Essencial** — entregável HTML |
| `logs.jsonl` | Zero | Storage mínimo | **Essencial** — rastreabilidade |
| Mock LLM | Zero | Zero | **Dev only** — não para avaliação final |

---

## 5. Oportunidades de redução de custo (sem trocar arquitetura)

Ordenadas por impacto e esforço.

### 5.1 Alto impacto, baixo esforço

| Otimização | Economia estimada | Esforço |
|---|---|---|
| Haiku no Agente 1, Sonnet no Agente 2 | ~65% no lote de 500 | Baixo — já suportado pelo `LLMClient` |
| Expandir rota expressa (urgência Crítica do Agente 1) | +10–20% chamadas evitadas | Médio — nova regra no grafo |
| Cache de chunks RAG (política estática) | Marginal em tokens | Baixo |
| `--limit` em dev; lote completo só na demo | 100% em dev | Já existe |

### 5.2 Médio impacto, médio esforço

| Otimização | Economia estimada | Esforço |
|---|---|---|
| Paralelismo (4 workers) | 0% em API; −60% em tempo | Médio |
| Pular Agente 2 quando categoria = Fraude/Segurança + BC | Variável | Médio |
| Resumo só via LLM nos casos sem palavrão/PII complexo | Pequena | Baixo |

### 5.3 Alto impacto, alto esforço (pós-desafio)

| Otimização | Economia estimada | Esforço |
|---|---|---|
| Laya no Agente 1, LLM só em ambíguos | ~40–65% em API | Alto — outro runtime |
| Resumo assíncrono (fila) | 0% API; −latência percebida | Alto |
| Fine-tune modelo pequeno no domínio | Variável | Muito alto |

---

## 6. Custo de infraestrutura (não-API)

Para o **desafio em si**, custo de infraestrutura é praticamente zero:

| Recurso | Custo no desafio | Custo em produção |
|---|---|---|
| Execução local (Python + venv) | US$ 0 | US$ 0 (dev) |
| Anthropic API (500 req, tiered) | ~US$ 3 | Escala linear |
| Bedrock (500 req) | Similar + egress AWS | + VPC, IAM, logging |
| Plotly (CDN no HTML) | US$ 0 | US$ 0 |
| Armazenamento `reports/` | Negligível | S3 / disco |

**Atenção ao edital:** qualquer recurso cloud pago deve ser desprovisionado após o evento.

---

## 7. Matriz decisão: qual arquitetura para qual contexto

| Contexto | Arquitetura recomendada | Custo 500 req | Latência |
|---|---|---:|---|
| Desenvolvimento / CI | Mock | US$ 0 | < 1 min |
| Demo ao vivo (banca) | Haiku + Sonnet + rota expressa | ~US$ 3 | ~15–25 min sequencial |
| Demo ao vivo (10 casos) | Haiku + Sonnet | < US$ 0,10 | < 1 min |
| Avaliação de qualidade | Sonnet em ambos agentes | ~US$ 10 | ~30–45 min |
| Produção (baixo volume) | Tiered + rota expressa expandida | Escala linear | Aceitável |
| Produção (alto volume) | Laya + LLM seletivo | Menor API | Menor latência ingestão |

---

## 8. Métricas a instrumentar (ainda não implementadas)

Para sustentar o argumento de custo na apresentação, registrar em `logs.jsonl`:

```json
{
  "agente": "agente_1_estruturacao",
  "provider": "anthropic",
  "modelo": "claude-haiku-4-5",
  "tokens_entrada": 1180,
  "tokens_saida": 165,
  "custo_usd_estimado": 0.00206,
  "rota": "llm"
}
```

Agregados úteis no relatório gerencial:

- Total de tokens e custo por lote.
- % de reclamações na rota expressa vs LLM.
- Custo médio por reclamação.
- Projeção mensal (reclamações/dia × 22 dias úteis).

---

## 9. Conclusão

1. **Para o desafio**, o custo absoluto de API é baixo (US$ 3–10 por lote completo). O argumento
   de custo deve focar em **proporção evitável** (rota expressa, tiering de modelos) e em
   **escalabilidade** (projeção para 1M).
2. A **melhoria imediata** é usar **Haiku no Agente 1** e **Sonnet no Agente 2**, sem alterar o
   grafo — economia de ~65% no lote com o mesmo desenho multi-agente.
3. A **rota expressa** já economiza ~17% vs LLM em tudo; expandir regras (urgência, categoria
   fraude) pode dobrar esse ganho.
4. A alternativa **Laya + LLM seletivo** é 44–65% mais barata em API, mas troca a narrativa do
   edital (agents com LLM) por eficiência operacional — usar como visão futura, não como entrega
   principal.

Ver também: `avaliacao_overkill.md` para componentes que não justificam custo adicional no escopo
do desafio.
