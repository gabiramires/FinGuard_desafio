"""Casos de uso — pipelines Nível 1 e Nível 2."""

from concurrent.futures import ThreadPoolExecutor, as_completed
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


def rodar_nivel1(ctx: PipelineContext, reclamacoes: list[dict], max_workers: int = 1) -> list[dict]:
    def _processar(reclamacao: dict) -> dict:
        analise, motivo_bloqueio = estruturacao.executar(
            reclamacao,
            ctx.llm,
            ctx.logger,
            prompt=ctx.prompt_estruturacao,
            rag=ctx.rag,
        )
        return {
            "id": reclamacao["id"],
            "canal": reclamacao.get("canal", ""),
            "data_reclamacao": reclamacao.get("data_reclamacao"),
            "texto_reclamacao": reclamacao["texto_reclamacao"],
            "analise": analise.model_dump(mode="json"),
            "parecer_risco": None,
            "bloqueado_seguranca": motivo_bloqueio is not None,
            "motivo_bloqueio": motivo_bloqueio,
        }

    return _executar_em_paralelo(reclamacoes, _processar, max_workers, rotulo="nível 1")


def rodar_nivel2(ctx: PipelineContext, reclamacoes: list[dict], max_workers: int = 1) -> list[dict]:
    config = GrafoConfig(llm=ctx.llm, logger=ctx.logger, pack=ctx.pack, rag=ctx.rag)
    app = construir_grafo(config)

    def _processar(reclamacao: dict) -> dict:
        return processar_reclamacao(app, reclamacao)

    return _executar_em_paralelo(reclamacoes, _processar, max_workers, rotulo="nível 2")


def _executar_em_paralelo(reclamacoes: list[dict], processar, max_workers: int, rotulo: str) -> list[dict]:
    total = len(reclamacoes)
    resultados: list[dict | None] = [None] * total

    if max_workers <= 1:
        for i, reclamacao in enumerate(reclamacoes):
            print(f"[{rotulo}] {i + 1}/{total} — {reclamacao['id']}")
            resultados[i] = processar(reclamacao)
        return resultados

    concluidos = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futuros = {executor.submit(processar, reclamacao): i for i, reclamacao in enumerate(reclamacoes)}
        for futuro in as_completed(futuros):
            i = futuros[futuro]
            resultados[i] = futuro.result()
            concluidos += 1
            print(f"[{rotulo}] {concluidos}/{total} — {reclamacoes[i]['id']}")

    return resultados
