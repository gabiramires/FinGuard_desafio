# Análise comparativa — FinGuard_desafio vs inference-triage

> Documento gerado em 22/09/2026. Compara o projeto de entrega do desafio Future Minds 3
> (`FinGuard_desafio`) com a POC de benchmark (`inference-triage`), no mesmo workspace.

## 1. Visão geral

Os dois projetos tratam o **mesmo domínio** (reclamações financeiras do desafio FinGuard), mas com
**objetivos diferentes**:

| Aspecto | `FinGuard_desafio` | `inference-triage` |
|---|---|---|
| Objetivo | Entregar o desafio Future Minds 3 | Estudar decisão barata vs geração cara |
| Arquitetura | CSV → LangGraph (3 agentes) → relatórios | CSV → decisor local (mock/Laya) → SQLite/JSON |
| LLM generativo | No centro (Agente 1 e Agente 2) | Fora do escopo V0 (planejado só para resumo/revisão) |
| Agentes | Sim — LangGraph com roteamento condicional | Não (deliberadamente) |
| RAG | Keyword sobre `ks_politica_interna.md` | Policy como asset; retrieval planejado |
| Avaliação | Sem métricas automatizadas de qualidade | Gates, benchmarks Docker, labels draft |
| Governança | Ofuscação só no resumo | Camada determinística de ameaças |

O `inference-triage` **critica explicitamente** a abordagem multi-agente antes de provar a
classificação básica (`concept/initial.md` no outro repo). O `FinGuard_desafio` **implementa o
edital** como foi pedido.

**Para a banca do desafio**, o `FinGuard_desafio` é o formato certo. O `inference-triage` é um
laboratório de engenharia e custo que pode alimentar decisões futuras.

---

## 2. O que o FinGuard_desafio já cobre bem

O esqueleto está **alinhado ao edital** e bem documentado em `analise_desafio.md` e `README.md`.

```text
CSV → Agente 1 (estruturação + RAG)
        → [condicional] risco_expresso (regra) | risco_completo (LLM)
        → Agente 3 (consolidação por reclamação)
        → relatorio.py (dashboard agregado do lote)
```

### Requisitos atendidos

| Requisito do edital | Status | Onde |
|---|---|---|
| Nível 1: categoria, produto, sentimento, urgência, resumo | Implementado | `schemas.py`, `agente1_estruturacao.py` |
| RAG sobre política interna | Implementado | `rag.py` |
| Ofuscação de palavrões no resumo | Implementado | `ofuscacao.higienizar` após o LLM |
| Saídas JSON/CSV/HTML | Implementado | `relatorio.py` |
| Nível 2 multi-agente com LangGraph | Implementado | `graph.py` |
| Agente 2: fraude, LGPD, reputacional, escalação | Implementado | `agente2_risco.py` |
| Relatório gerencial (dashboard, críticas, recomendações) | Implementado | `montar_dashboard` |
| Fluxo condicional | Implementado | BC → `executar_expresso` sem LLM |
| Logs por agente (entrada/saída/tempo) | Implementado | `reports/logs.jsonl` |
| Execução local, sem cloud storage | OK | Saídas em `reports/` |
| Otimização de custo (bônus) | Parcial | Rota expressa existe, sem métricas |

### Decisões de design corretas

- **Dashboard fora do grafo:** Agente 3 empacota por reclamação; `relatorio.py` agrega o lote inteiro.
  Faz sentido operacionalmente e deve ser explicado no pitch.
- **Mesmo Agente 1 nos dois níveis:** evita duplicação entre classificador isolado e primeiro nó do
  grafo.
- **Provider trocável:** `LLMClient` com mock, Anthropic e Bedrock sem alterar código dos agentes.
- **Dataset oficial presente:** `data/dataset_finguard_desafio_3.csv` (500 registros). O README ainda
  menciona apenas a amostra de 10 linhas — precisa atualização.

---

## 3. Lacunas e fragilidades

Priorizado pelos **pesos do edital** (Funcionalidade 30%, IA 20%, Arquitetura 20%, Segurança 15%,
Apresentação 15%).

### 3.1 Funcionalidade (30%)

- Pipeline validado ponta a ponta com **mock**, não com LLM real.
- Mock é heurística por palavra-chave; erra casos que exigem nuance (ex.: juros de empréstimo →
  "Outros").
- `bedrock` implementado mas não testado contra conta AWS real.
- Sem gold labels nem métricas (accuracy, F1 por categoria).

### 3.2 Segurança e governança (15%) — gap crítico

O dataset contém dezenas de **ataques de prompt injection** e pedidos de exfiltração de dados. O
projeto não tem camada de detecção equivalente ao `rules.ts` do `inference-triage`.

Problemas concretos:

- `mascarar_dados_pessoais` só roda no **resumo** do Agente 1.
- `resultados_nivel2.json` exporta `texto_reclamacao` integral (CPF, conta, palavrões).
- Justificativas do Agente 2 podem repetir PII do texto original.
- Relatório gerencial lista justificativas sem sanitização adicional.
- Nenhum guardrail impede o LLM de vazar o system prompt em ataques.

### 3.3 Uso de ferramentas de IA (20%)

- Falta narrativa de custo: tokens por reclamação, % na rota expressa, economia estimada.
- `LLMClient` suporta modelos diferentes por agente, mas `main.py` usa uma única instância.
- Sem evidência de que o RAG melhora a classificação (A/B com e sem contexto).

### 3.4 Arquitetura e design (20%)

| Extensão incentivada no edital | Status |
|---|---|
| Roteamento condicional | Feito |
| Paralelismo | Não implementado |
| Loops de validação | Não implementado |
| Rastreabilidade em tempo real | Parcial (só `logs.jsonl` post-hoc) |

**Nota sobre Agente 3:** o edital descreve "Relatório Gerencial"; na implementação é consolidação +
relatório batch. Funciona, mas merece ADR para não confundir a banca.

### 3.5 Apresentação (15%)

- Sem ADR formal.
- Sem pitch script ou demo documentada.
- Sem análise de custo para apresentação (ver `avaliacao_custo.md`).

---

## 4. Lacunas técnicas específicas

### Qualidade da classificação

O `inference-triage` possui `labels-ai-draft-v2.csv` e gates em `checks/gates/finguard-v0.json`.
Benchmark Laya recente: ~46% concordância em categoria, ~78% em produto (comparação exploratória,
não gold oficial).

### RAG

Retrieval por keyword funciona para documento único e curto, mas falha quando não há overlap lexical
entre consulta e seção da política.

### Produto vazio no CSV

24,4% dos registros do dataset oficial não trazem `produto`. O Agente 1 passa o campo informado,
mas não há política explícita do tipo `source_if_known` (usar CSV quando preenchido, inferir só
quando vazio).

### Rota expressa e canais

A regra de canal crítico cobre **Banco Central** e **Procon**. No dataset oficial, os canais são
apenas: SAC (133), Ouvidoria (127), Banco Central (121), Redes Sociais (119). **Procon não aparece
como valor de canal** — a rota expressa atinge 121/500 registros (24,2%).

### Testes automatizados

O `inference-triage` tem testes unitários, e2e e contratos. O `FinGuard_desafio` não tem testes.

Mínimo recomendado:

- Grafo: BC → rota expressa.
- Ofuscação: CPF, palavrão.
- Schemas: enums válidos.
- Relatório gerencial não contém CPF.

---

## 5. O que absorver do inference-triage

| Peça do `inference-triage` | Uso no `FinGuard_desafio` |
|---|---|
| `detectThreats` / rules determinísticas | Guardrails contra injection e exfiltração |
| Gates + labels draft | Provar qualidade da classificação |
| `productPolicy: source_if_known` | Respeitar produto do CSV quando preenchido |
| Hashes de dataset/config | Reprodutibilidade da demo |
| `justification.md` | Argumento de custo na apresentação |
| Separação decisão vs geração | Expandir rotas sem LLM além de BC/Procon |

---

## 6. Roadmap sugerido

### Fase A — Entrega para a banca (1–2 dias)

1. Atualizar README (dataset completo, comandos reais).
2. Validar com provider real (`anthropic` ou `bedrock`) nas 500 reclamações.
3. Adicionar guardrails (detecção + sanitização de exports).
4. Remover `texto_reclamacao` do relatório gerencial; mascarar justificativas.
5. Script de demo documentado.

### Fase B — Diferenciais (2–3 dias)

6. Métricas de custo no `logs.jsonl` (tokens in/out por agente).
7. Modelo menor no Agente 1, maior no Agente 2 (com justificativa).
8. Paralelismo (`--workers 4`).
9. Loop de validação (ex.: urgência Crítica + categoria Outros → re-prompt).
10. Testes automatizados mínimos.

### Fase C — Apresentação

11. ADR de 1–2 páginas.
12. Slide de custo: mock vs LLM full vs LLM com rota expressa.
13. Demo ao vivo: caso normal, crítico BC, injection bloqueado.

---

## 7. Resumo executivo

| Dimensão | Status | Gap principal |
|---|---|---|
| Arquitetura multi-agente | Pronto | Documentar Agente 3 vs relatório batch |
| Nível 1 + 2 | Pronto | Validar com LLM real |
| RAG | Básico, funcional | Medir impacto |
| Governança | Fraco | Guardrails, PII nos exports, anti-injection |
| Qualidade | Não medida | Benchmark contra labels |
| Custo | Rota expressa sem métricas | Contabilizar tokens (ver `avaliacao_custo.md`) |
| Testes / CI | Ausente | Mínimo para demo confiável |
| Apresentação | Parcial | ADR + pitch + demo script |

O projeto está em **~70% do caminho** para uma entrega forte. Os 30% restantes são principalmente
**segurança, validação com LLM real e material de apresentação** — não redesign arquitetural.

### Narrativa recomendada para a banca

> Implementamos o fluxo multi-agente do edital. A rota expressa e guardrails determinísticos
> reduzem custo e risco. Para escala, a decisão estruturada pode migrar para modelo local (Laya),
> reservando LLM para resumo e casos ambíguos.

Isso demonstra domínio do edital **e** visão de engenharia além dele.

---

## 8. Documentos relacionados neste repositório

| Arquivo | Conteúdo |
|---|---|
| `analise_desafio.md` | Leitura do edital |
| `avaliacao_custo.md` | Projeção de custo por arquitetura |
| `avaliacao_overkill.md` | O que é excesso para o escopo do desafio |
| `README.md` | Setup e mapeamento de requisitos |
