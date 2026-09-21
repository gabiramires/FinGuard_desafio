"""Agente 2 — Análise de Risco e Conformidade.

Duas rotas, escolhidas pelo grafo (ver graph.py):

- executar_completo: caminho padrão, usa o LLM para avaliar fraude,
  violação regulatória, risco reputacional e necessidade de escalação.
- executar_expresso: caminho de custo zero em LLM, usado quando a própria
  política interna já determina o resultado por regra (seção 4.3: canal
  Banco Central/Procon = urgência automaticamente crítica). Isso é o
  roteamento condicional + otimização de custo citados no edital.
"""

import time

from .. import rag
from ..llm_client import LLMClient
from ..logging_utils import AgentLogger
from ..schemas import AnaliseEstruturada, NivelRisco, ParecerRisco

NOME_AGENTE_COMPLETO = "agente_2_risco_completo"
NOME_AGENTE_EXPRESSO = "agente_2_risco_expresso"

PROMPT_SISTEMA = """Você é o analista de risco e conformidade de uma instituição financeira.
Avalie a análise estruturada da reclamação abaixo e determine o nível de risco regulatório e
reputacional, segundo a política interna fornecida como contexto.

Pontos de verificação obrigatórios: indício de fraude ou transação não autorizada; violação de
regulamento (LGPD, sigilo bancário); risco reputacional (imprensa, redes sociais, órgãos
reguladores); necessidade de escalação imediata para compliance.

Trecho da política interna relevante:
{contexto}

Nível de risco possível: Baixo, Médio, Alto, Crítico. A justificativa deve ser objetiva e citar
o indício encontrado e, quando aplicável, a regra da política que se aplica."""


def _prompt_usuario(reclamacao: dict, analise: AnaliseEstruturada) -> str:
    return (
        f"Canal: {reclamacao.get('canal', 'não informado')}\n"
        f"Categoria: {analise.categoria.value}\n"
        f"Produto: {analise.produto.value}\n"
        f"Sentimento: {analise.sentimento.value}\n"
        f"Urgência (agente 1): {analise.urgencia.value}\n"
        f"Resumo: {analise.resumo}\n"
        f"Texto original da reclamação:\n{reclamacao['texto_reclamacao']}"
    )


def executar_completo(
    reclamacao: dict, analise: AnaliseEstruturada, llm: LLMClient, logger: AgentLogger
) -> ParecerRisco:
    inicio = time.perf_counter()

    contexto = rag.buscar_contexto(
        f"{reclamacao['texto_reclamacao']} fraude lgpd risco reputacional escalacao {analise.urgencia.value}"
    )
    system = PROMPT_SISTEMA.format(contexto=contexto or "(nenhum trecho relevante encontrado)")
    user = _prompt_usuario(reclamacao, analise)

    parecer = llm.gerar_estruturado(system, user, ParecerRisco)

    duracao_ms = (time.perf_counter() - inicio) * 1000
    logger.registrar(reclamacao["id"], NOME_AGENTE_COMPLETO, user, parecer.model_dump(mode="json"), duracao_ms)
    return parecer


def executar_expresso(reclamacao: dict, analise: AnaliseEstruturada, logger: AgentLogger) -> ParecerRisco:
    """Sem chamada de LLM: o canal já determina Crítico por regra de negócio (política 4.3)."""
    inicio = time.perf_counter()

    contexto = rag.contexto_secao_canal(reclamacao.get("canal", ""))
    parecer = ParecerRisco(
        nivel_risco=NivelRisco.CRITICO,
        justificativa=(
            f"Canal de origem '{reclamacao.get('canal')}' torna a urgência automaticamente crítica "
            "conforme seção 4.3 da política interna (POL-SAC-001) — resposta revisada pelo jurídico "
            "e Compliance notificado em até 2h."
        ),
        indicios_fraude="fraude" in reclamacao["texto_reclamacao"].lower(),
        indicios_violacao_regulatoria=False,
        risco_reputacional=True,
        necessita_escalacao_imediata=True,
    )

    duracao_ms = (time.perf_counter() - inicio) * 1000
    logger.registrar(
        reclamacao["id"],
        NOME_AGENTE_EXPRESSO,
        {"canal": reclamacao.get("canal"), "contexto_politica": contexto},
        parecer.model_dump(mode="json"),
        duracao_ms,
    )
    return parecer
