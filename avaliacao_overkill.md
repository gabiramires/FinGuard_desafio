# Avaliação de arquitetura — o que é overkill para o desafio

> Documento gerado em 22/09/2026. Identifica complexidade desnecessária, componentes prematuros e
> alternativas mais simples que atendem o edital Future Minds 3 sem sacrificar os critérios de
> avaliação.

## 1. Critério de julgamento

Um componente é **overkill** quando:

- não responde a um requisito do edital nem a um critério de avaliação;
- adiciona complexidade operacional sem ganho demonstrável na demo;
- pode ser substituído por algo mais simples com o mesmo resultado percebido pela banca;
- é prematuro para 500 reclamações em execução local.

Um componente **não é overkill** mesmo sendo simples, se o edital pede explicitamente (ex.:
LangGraph, RAG, relatório gerencial).

---

## 2. Mapa rápido: necessário vs excesso

| Componente | Veredicto | Motivo |
|---|---|---|
| LangGraph com 3 agentes | **Necessário** | Edital pede multi-agente; LangGraph é recomendado |
| RAG keyword sobre política única | **Adequado** | Documento curto; vector store seria overkill |
| Provider mock para dev | **Adequado** | Sem custo em desenvolvimento |
| Rota expressa BC/Procon | **Adequado** | Bônus de custo com implementação mínima |
| Plotly no HTML | **Adequado** | Edital pede gráfico; Plotly é a opção mais rápida |
| Pydantic + tool-calling | **Adequado** | Garante saída estruturada sem parsing frágil |
| Agente 3 como nó do grafo | **Discutível** | Só empacota JSON; poderia ser função pós-grafo |
| Vector DB / embeddings | **Overkill** | Política tem ~145 linhas; keyword resolve |
| Microserviços / API REST | **Overkill** | Edital é batch local sobre CSV |
| Fila distribuída (Redis, SQS) | **Overkill** | 500 registros, execução única |
| SQLite / banco relacional | **Overkill** | JSON/CSV atendem o edital |
| Kubernetes / Docker obrigatório | **Overkill** | Não pedido; complexidade de demo |
| Fine-tuning de modelo | **Overkill** | Escopo de pesquisa, não de hackathon |
| Laya / ONNX no desafio | **Overkill agora** | Outra arquitetura; confunde narrativa agents |
| Múltiplos prompts versionados em assets | **Overkill** | Útil em produção; prompts inline bastam |
| Dashboard em tempo real (WebSocket) | **Overkill** | Relatório estático ao final basta |
| Human-in-the-loop | **Overkill** | Mencionado como extensão, não requisito |
| Paralelismo agressivo (8+ workers) | **Overkill** | 500 req em sequência roda em < 30 min |
| Testes e2e com LLM real no CI | **Overkill** | Caro e instável; testes unitários bastam |
| Observabilidade (Datadog, Grafana) | **Overkill** | `logs.jsonl` atende rastreabilidade do edital |

---

## 3. Análise por camada

### 3.1 Orquestração

#### LangGraph — **não é overkill**

O edital recomenda LangGraph para o Nível 2. O grafo atual é enxuto:

```text
start → agente_1 → [condicional] → risco_expresso | risco_completo → agente_3 → end
```

Alternativa mais simples (loop `for` com `if canal`): funcionaria, mas **perderia pontos** em
Arquitetura (20%) e Uso de IA (20%). Manter LangGraph.

#### Agente 3 no grafo — **levemente overkill**

Hoje o Agente 3 apenas monta `RegistroReclamacao` sem LLM. Poderia ser uma função chamada após o
grafo:

```python
# Mais simples, mesmo resultado
analise, parecer = grafo.invoke(...)
registro = consolidar(reclamacao, analise, parecer)
```

**Manter no grafo** se a banca espera literalmente três agentes no diagrama. **Mover para função**
se quiser simplificar sem perder funcionalidade — o edital não exige que o Agente 3 seja um nó
LangGraph, só que exista consolidação.

#### Relatório gerencial fora do grafo — **correto, não é overkill**

Dashboard agregado por lote não faz sentido por reclamação. A decisão de `relatorio.py` pós-loop é
a mais simples que funciona.

---

### 3.2 RAG

#### RAG por keyword — **adequado**

| Abordagem | Complexidade | Quando justifica |
|---|---|---|
| Keyword overlap (atual) | Baixa | Documento único < 200 linhas |
| Embeddings + Chroma/FAISS | Média | Múltiplos documentos ou política > 50 páginas |
| RAG híbrido + reranker | Alta | Produção com SLA de precisão |

A política `ks_politica_interna.md` tem seções numeradas e vocabulário repetível. Embeddings
adicionariam dependência (`sentence-transformers`, índice, tempo de build) sem ganho mensurável
na demo.

**Overkill:** vector store, chunking semântico avançado, múltiplas fontes, graph RAG.

**Não overkill:** `buscar_contexto` atual com `k=3` chunks.

---

### 3.3 LLM e providers

#### Três providers (mock, anthropic, bedrock) — **adequado**

Mock para dev; um provider real para demo. Implementar os dois clouds é **ligeiramente overkill**
se só um será usado na apresentação — mas justifica-se em "Uso de Ferramentas de IA" se Bedrock
for mencionado no pitch.

**Overkill:** quarto provider, fallback automático entre clouds, circuit breaker.

#### Mesmo modelo nos dois agentes — **subótimo, não overkill**

Usar Sonnet em tudo é caro, mas simples. O overkill seria adicionar um **router de modelo por
complexidade** com ML; o adequado é passar `model=` diferente ao instanciar dois `LLMClient`.

#### Loops de validação com re-prompt — **overkill para demo, útil em produção**

Ex.: "se categoria=Outros e urgência=Crítica, reclassificar". Melhora qualidade, mas aumenta
custo (até 2× chamadas) e complexidade. Para o desafio: **opcional**, só se houver tempo e
métricas mostrando ganho.

---

### 3.4 Segurança

Paradoxalmente, **a camada de segurança é onde o projeto está subdimensionado**, não
over-engineered.

| Medida | Overkill? | Observação |
|---|---|---|
| Ofuscar palavrões no resumo | Não | Requisito explícito |
| Mascarar CPF no resumo | Não | Requisito de governança |
| `detectThreats` determinístico | Não | Dataset tem injection; 15% da nota |
| WAF / firewall de LLM comercial | Sim | Regex local basta |
| Classificador ML de injection | Sim | Regras cobrem os casos do dataset |
| Criptografia em repouso dos reports | Sim | Execução local, sem persistência cloud |
| Auditoria SOC2 | Sim | Fora do escopo |

**Overkill:** comprar produto de guardrails. **Necessário:** 50–80 linhas de detecção + sanitizar
exports.

---

### 3.5 Relatórios e visualização

#### Plotly com CDN — **adequado**

Alternativas mais simples: gráficos ASCII no Markdown, matplotlib estático. Plotly entrega HTML
interativo com poucas linhas — bom custo/benefício.

**Overkill:** dashboard React separado, BI (Metabase, Superset), API para frontend.

#### Quatro formatos de saída (JSON, CSV, HTML, MD) — **adequado**

O edital pede JSON/CSV/HTML. Markdown é bônus útil para o pitch. Não cortar.

---

### 3.6 Infraestrutura e operação

| Item | Veredicto |
|---|---|
| `python main.py` + CSV | Ideal para o desafio |
| API FastAPI + fila | Overkill |
| Docker Compose | Opcional; útil para reprodutibilidade, não obrigatório |
| Terraform / IaC | Overkill |
| CI com GitHub Actions (lint + testes unitários) | Adequado |
| CI chamando LLM real | Overkill (custo + flakiness) |
| Makefile | Adequado (DX) |

---

### 3.7 O que o `inference-triage` faz que seria overkill aqui

O outro projeto no workspace é deliberadamente mais pesado em engenharia de benchmark. Trazer para
o desafio seria overkill:

| Peça do inference-triage | Por que é overkill no desafio |
|---|---|
| Benchmark Docker com CPU/memória fixa | Avaliação é demo funcional, não SRE |
| Hashes SHA256 de dataset/prompt/taxonomy | Útil em pesquisa; banca não pede |
| Gates JSON com macro-F1 mínimo | Sem gold oficial do desafio |
| SQLite com classes de dados restrito/público | Edital aceita JSON local |
| Múltiplas variantes de prompt (v1, v2, v3) | Iteração de pesquisa |
| Export ONNX / Laya multilíngue | Outro paradigma arquitetural |
| `evaluate-gates.mjs` | Pipeline de CI de benchmark |

**Exceção — não é overkill portar:** `detectThreats` (poucas linhas, alto impacto em Segurança 15%).

---

## 4. Simplificações recomendadas (menos código, mesmo score)

Ordem de prioridade: maior redução de complexidade com menor perda de pontos.

### 4.1 Fazer

1. **Manter LangGraph** com o grafo mínimo atual.
2. **Manter RAG keyword** — não migrar para embeddings.
3. **Adicionar guardrails leves** (regex) — reduz risco sem inflar arquitetura.
4. **Usar um provider real** na demo; mock só em dev.
5. **Tiering de modelo** (Haiku + Sonnet) — menos custo, mesma arquitetura.

### 4.2 Não fazer (agora)

1. Vector database.
2. API HTTP / microserviços.
3. Fila assíncrona / workers distribuídos.
4. Integrar Laya no fluxo principal (confunde a narrativa agents).
5. Fine-tuning ou RAG sobre o dataset de reclamações.
6. Dashboard real-time.
7. Múltiplos ambientes cloud.

### 4.3 Considerar remover ou simplificar

| Item atual | Simplificação | Impacto na nota |
|---|---|---|
| Agente 3 como nó LangGraph | Função `consolidar()` pós-grafo | Nenhum, se relatório final igual |
| Provider Bedrock | Só Anthropic na demo | Mínimo, se não for mencionar AWS |
| `exportar_markdown` | Manter — custo zero | Positivo para apresentação |
| Mock LLM elaborado (~190 linhas) | Reduzir para ~50 linhas | Nenhum em produção |

---

## 5. Arquitetura mínima que maximiza a nota

```text
┌─────────────────────────────────────────────────────────────┐
│  CLI (main.py)                                              │
│    CSV → loop sequencial                                    │
│      → LangGraph                                            │
│          agente_1 (Haiku + RAG keyword + higienizar resumo) │
│          → if canal_crítico: regra                          │
│            else: agente_2 (Sonnet + RAG)                    │
│          → consolidar registro                              │
│      → relatorio.py (dashboard HTML + JSON/CSV)             │
│      → logs.jsonl + guardrails regex                        │
└─────────────────────────────────────────────────────────────┘
```

Componentes **fora** deste desenho mínimo só entram se houver evidência de ganho na demo:

- Paralelismo → se demo de 500 req precisar terminar em < 10 min.
- Loop de validação → se métricas mostrarem erro sistemático.
- Bedrock → se o pitch for especificamente "AWS AI".

---

## 6. Anti-padrões observados (evitar na apresentação)

1. **Demonstrar só com mock** — a banca percebe heurística vs IA real.
2. **Explicar embeddings** sem ter implementado — parece overkill teórico.
3. **Prometer escala a 1M** sem números — usar `avaliacao_custo.md`.
4. **Mostrar JSON com CPF** no relatório — falha em Governança (15%).
5. **Diagrama com 8 caixas** quando o código tem 4 — inconsistência arquitetural.
6. **Copiar inference-triage inteiro** — troca agents por benchmark; perde o edital.

---

## 7. Conclusão

O `FinGuard_desafio` está **no ponto certo de complexidade** para o desafio: multi-agente com
LangGraph, RAG simples, relatório gerencial, rota expressa. Não precisa de vector DB, fila,
microserviços nem modelo local.

Os únicos ajustes que **aumentam nota sem inflar arquitetura**:

| Ajuste | Esforço | Critério beneficiado |
|---|---|---|
| Guardrails regex + sanitizar exports | Baixo | Segurança 15% |
| Haiku/Sonnet tiered | Baixo | IA 20% + bônus custo |
| Demo com LLM real nas 500 | Médio | Funcionalidade 30% |
| ADR + script de pitch | Baixo | Apresentação 15% |
| Testes unitários (grafo, ofuscação) | Baixo | Funcionalidade + confiança na demo |

O que **seria overkill adicionar agora**: embeddings, API, Docker obrigatório, Laya, CI com LLM,
observabilidade comercial, loops de re-prompt sem métrica.

Ver também: `avaliacao_custo.md` para números e `analise_comparativa.md` para o panorama completo
entre os dois projetos do workspace.
