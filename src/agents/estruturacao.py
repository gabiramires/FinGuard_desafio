"""Agente de estruturação — Nível 1."""

from src.agents.base import LLMStructuredAgent
from src.domain.models import AnaliseEstruturada
from src.infrastructure.llm.client import LLMGateway
from src.infrastructure.logging.agent_logger import AgentLogger
from src.infrastructure.rag.politica import PoliticaRAG
from src.prompts.loader import PromptAsset
from src.shared.ofuscacao import higienizar

NOME_AGENTE = "agente_1_estruturacao"


def _contexto_estruturacao(rag: PoliticaRAG, reclamacao: dict, **_extras) -> str:
    consulta = f"{reclamacao['texto_reclamacao']} {reclamacao.get('produto') or ''} {reclamacao.get('canal', '')}"
    return rag.buscar_contexto(consulta)


def _pos_processar_resumo(analise: AnaliseEstruturada) -> AnaliseEstruturada:
    analise.resumo = higienizar(analise.resumo)
    return analise


def criar_agente_estruturacao(
    prompt: PromptAsset,
    llm: LLMGateway,
    rag: PoliticaRAG | None = None,
) -> LLMStructuredAgent:
    rag = rag or PoliticaRAG()
    return LLMStructuredAgent(
        prompt=prompt,
        llm=llm,
        rag_contexto=lambda reclamacao, **_extras: _contexto_estruturacao(rag, reclamacao),
        pos_processar=_pos_processar_resumo,
    )


def executar(
    reclamacao: dict,
    llm: LLMGateway,
    logger: AgentLogger,
    *,
    prompt: PromptAsset | None = None,
    rag: PoliticaRAG | None = None,
) -> tuple[AnaliseEstruturada, str | None]:
    from src.prompts.loader import carregar_pack

    prompt = prompt or carregar_pack().prompts["estruturacao"]
    agente = criar_agente_estruturacao(prompt, llm, rag)
    return agente.executar(reclamacao, logger)  # type: ignore[return-value]
