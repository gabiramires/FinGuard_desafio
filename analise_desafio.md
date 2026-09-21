# Análise do Desafio — FinGuard: Assistente Inteligente de Análise de Reclamações

## 1. Problema de negócio

Instituições financeiras recebem reclamações por múltiplos canais (SAC, Ouvidoria, Banco Central, Procon,
Redes Sociais), em texto livre, sem padronização. Hoje a triagem é manual: um analista lê, classifica,
identifica produto, avalia criticidade e encaminha. É lento, inconsistente entre analistas e frágil em picos
de volume.

**Objetivo do desafio:** construir o FinGuard, um sistema que automatiza esse fluxo — da triagem inicial até
relatórios acionáveis para a gestão — usando IA (LLMs, agentes, RAG).

## 2. Dataset

CSV fornecido pela Future Minds, ~500 reclamações fictícias:

| Campo | Descrição |
|---|---|
| `id` | Identificador único (ex.: `REC-2026-00142`) |
| `data_reclamacao` | Data do registro |
| `canal` | SAC, Ouvidoria, Banco Central, Redes Sociais |
| `texto_reclamacao` | Texto livre — informal, com erros, palavrões, urgência variável |
| `produto` | Pode estar **vazio** — precisa ser inferido quando ausente |
| `status` | Aberta, Em análise, Resolvida |

Dados imperfeitos de propósito: tom variável, complexidade variável (reclamação simples vs. indício de
fraude), completude variável (produto às vezes ausente). O sistema precisa lidar com isso sem quebrar.

## 3. Estrutura em níveis

### Nível 1 — Classificador Inteligente

Entrada: texto de uma reclamação. Saída estruturada (JSON):

```json
{
  "categoria": "Cobrança Indevida | Atendimento | Fraude/Segurança | Produto/Serviço | Cancelamento | Outros",
  "produto": "Cartão de Crédito | Conta Corrente | Empréstimo | Investimentos | Seguros | Não Identificado",
  "sentimento": "Positivo | Neutro | Negativo | Crítico",
  "urgencia": "Baixa | Média | Alta | Crítica",
  "resumo": "2-3 linhas, linguagem padronizada, palavrões ofuscados"
}
```

Requisitos-chave:
- RAG sobre a Política Interna (POL-SAC-001) para contextualizar categoria/produto/urgência.
- Ofuscação de palavras impróprias no resumo.
- Entregáveis: `.html` com gráfico dos resultados + `.json`/`.csv` com resultado por reclamação.
- Execução local, sem persistência em nuvem (proibido usar S3 etc. para os dados/resultados do desafio).

### Nível 2 — Orquestrador de Análise (multi-agente, LangGraph recomendado)

Evolui o Nível 1 para um grafo de agentes especializados:

```
_start_ → agente_1 (Recepção/Estruturação) → agente_2 (Risco/Conformidade) → agente_3 (Relatório) → __end__
```

- **Agente 1 — Recepção e Estruturação:** recebe a reclamação bruta, produz a saída estruturada do Nível 1
  (categoria, produto, sentimento, urgência, resumo).
- **Agente 2 — Análise de Risco e Conformidade:** avalia a saída do Agente 1 quanto a fraude/transação não
  autorizada, violação regulatória (LGPD, sigilo bancário), risco reputacional (imprensa/redes/reguladores),
  necessidade de escalação. Saída: nível de risco (Baixo/Médio/Alto/Crítico) + justificativa.
- **Agente 3 — Relatório Gerencial:** consolida tudo em relatório (JSON/Markdown/HTML) com dashboard
  (totais por categoria/produto/urgência), lista de reclamações críticas com parecer de risco, e
  recomendações de ação.

Extensões incentivadas (não obrigatórias, mas valorizadas): roteamento condicional (crítico pula direto
para o agente de risco), paralelismo (múltiplas reclamações simultâneas), loops de validação.

Requisitos não funcionais do Nível 2:
- Logs de execução de cada agente (entrada, saída, tempo de resposta).
- Fluxo rastreável — saber em qual agente cada reclamação está.
- Relatório final em arquivo ao término do processamento.
- Ainda sem persistência em serviços de nuvem.

## 4. Critérios de avaliação (pesos)

| Critério | Peso | O que olha |
|---|---|---|
| Funcionalidade | 30% | Funciona de verdade? Demonstração ao vivo. |
| Uso de Ferramentas de IA | 20% | Copilot/Bedrock/Iara — uso justificado |
| Arquitetura e Design | 20% | Separação de responsabilidades, clareza do fluxo |
| Segurança e Governança | 15% | Guardrails, proteção de dados, consciência de riscos |
| Apresentação e Justificativa | 15% | Pitch, ADR, justificativa de custos |

Pergunta obrigatória da banca: quais ferramentas de IA foram usadas e como contribuíram.
Bônus: otimização de custo (ex.: modelo menor para tarefas simples, modelo maior só onde precisa).

## 5. Restrições (compromisso)

- Usar **apenas** o dataset fornecido — proibido qualquer dado real de cliente/produção.
- Executar apenas nos ambientes designados para o desafio — nada de ambientes corporativos reais.
- Qualquer recurso cloud pago criado para o desafio deve ser desprovisionado imediatamente após o evento.
- Nenhum dado pessoal (CPF, conta, cartão) pode aparecer em relatórios gerenciais (ver política interna).

## 6. Implicações práticas para a implementação

- **RAG** é sobre a política interna (documento único, curto) — não precisa de um pipeline de RAG pesado;
  o desafio de engenharia real está na **extração estruturada consistente** via LLM e na **orquestração**
  entre agentes, não na complexidade do retrieval.
- O **mesmo código de agente 1** (classificação) serve tanto para o Nível 1 isolado quanto como primeiro nó
  do grafo do Nível 2 — vale desenhar já pensando nos dois níveis, sem redesenhar depois.
- Palavras impróprias / PII precisam de tratamento explícito no resumo e no relatório (governança = 15% da
  nota, não é só "nice to have").
- Rastreabilidade e logging não são triviais no Nível 1, mas passam a ser requisito formal no Nível 2 —
  vale instrumentar desde o início mesmo que "por baixo".
