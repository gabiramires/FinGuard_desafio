"""Agente de risco e conformidade — Nível 2."""

import time

from src.domain.enums import NivelRisco
from src.domain.models import AnaliseEstruturada, ParecerRisco
from src.infrastructure.llm.client import LLMGateway
from src.infrastructure.logging.agent_logger import AgentLogger
from src.infrastructure.rag.politica import PoliticaRAG
from src.prompts.loader import PromptAsset
from src.agents.base import LLMStructuredAgent

NOME_AGENTE_COMPLETO = "agente_2_risco_completo"
NOME_AGENTE_EXPRESSO = "agente_2_risco_expresso"


def _contexto_risco(rag: PoliticaRAG, reclamacao: dict, **extras) -> str:
    analise: AnaliseEstruturada | None = extras.get("analise")
    urgencia = analise.urgencia.value if analise else ""
    consulta = f"{reclamacao['texto_reclamacao']} fraude lgpd risco reputacional escalacao {urgencia}"
    return rag.buscar_contexto(consulta)


def criar_agente_risco(
    prompt: PromptAsset,
    llm: LLMGateway,
    rag: PoliticaRAG | None = None,
) -> LLMStructuredAgent:
    rag = rag or PoliticaRAG()

    return LLMStructuredAgent(
        prompt=prompt,
        llm=llm,
        rag_contexto=lambda reclamacao, **extras: _contexto_risco(rag, reclamacao, **extras),
    )


def executar_completo(
    reclamacao: dict,
    analise: AnaliseEstruturada,
    llm: LLMGateway,
    logger: AgentLogger,
    *,
    prompt: PromptAsset | None = None,
    rag: PoliticaRAG | None = None,
) -> ParecerRisco:
    from src.prompts.loader import carregar_pack

    prompt = prompt or carregar_pack().prompts["risco"]
    agente = criar_agente_risco(prompt, llm, rag)
    return agente.executar(reclamacao, logger, analise=analise)  # type: ignore[return-value]


def executar_expresso(
    reclamacao: dict,
    analise: AnaliseEstruturada,
    logger: AgentLogger,
    *,
    rag: PoliticaRAG | None = None,
) -> ParecerRisco:
    rag = rag or PoliticaRAG()
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
        prompt_version="regra-deterministica-4.3",
        output_model="ParecerRisco",
    )
    return parecer
