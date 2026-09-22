"""Casos de uso — pipelines Nível 1 e Nível 2."""

from dataclasses import dataclass

from src.agents import estruturacao
from src.application.graph import GrafoConfig, construir_grafo, processar_reclamacao
from src.infrastructure.llm.client import LLMGateway
from src.infrastructure.logging.agent_logger import AgentLogger
from src.infrastructure.rag.politica import PoliticaRAG
from src.prompts.loader import DomainPack, PromptAsset, carregar_pack


@dataclass
class PipelineContext:
    llm: LLMGateway
    logger: AgentLogger
    pack: DomainPack
    rag: PoliticaRAG
    prompt_estruturacao: PromptAsset


def criar_contexto(llm: LLMGateway, logger: AgentLogger, pack: DomainPack | None = None) -> PipelineContext:
    pack = pack or carregar_pack()
    rag = PoliticaRAG(pack.policy_path)
    return PipelineContext(
        llm=llm,
        logger=logger,
        pack=pack,
        rag=rag,
        prompt_estruturacao=pack.prompts["estruturacao"],
    )


def rodar_nivel1(ctx: PipelineContext, reclamacoes: list[dict]) -> list[dict]:
    resultados = []
    for i, reclamacao in enumerate(reclamacoes, start=1):
        print(f"[nível 1] {i}/{len(reclamacoes)} — {reclamacao['id']}")
        analise = estruturacao.executar(
            reclamacao,
            ctx.llm,
            ctx.logger,
            prompt=ctx.prompt_estruturacao,
            rag=ctx.rag,
        )
        resultados.append(
            {
                "id": reclamacao["id"],
                "canal": reclamacao.get("canal", ""),
                "data_reclamacao": reclamacao.get("data_reclamacao"),
                "texto_reclamacao": reclamacao["texto_reclamacao"],
                "analise": analise.model_dump(mode="json"),
                "parecer_risco": None,
            }
        )
    return resultados


def rodar_nivel2(ctx: PipelineContext, reclamacoes: list[dict]) -> list[dict]:
    config = GrafoConfig(llm=ctx.llm, logger=ctx.logger, pack=ctx.pack, rag=ctx.rag)
    app = construir_grafo(config)
    resultados = []
    for i, reclamacao in enumerate(reclamacoes, start=1):
        print(f"[nível 2] {i}/{len(reclamacoes)} — {reclamacao['id']}")
        resultados.append(processar_reclamacao(app, reclamacao))
    return resultados
