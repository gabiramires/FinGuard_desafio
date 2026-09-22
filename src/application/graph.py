"""Orquestração Nível 2 com LangGraph."""

from typing import Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from src.agents import consolidacao, estruturacao, risco
from src.domain.models import AnaliseEstruturada, ParecerRisco
from src.infrastructure.llm.client import LLMGateway
from src.infrastructure.logging.agent_logger import AgentLogger
from src.infrastructure.rag.politica import PoliticaRAG
from src.prompts.loader import DomainPack, PromptAsset, carregar_pack


class EstadoReclamacao(TypedDict):
    reclamacao: dict
    analise: Optional[dict]
    parecer_risco: Optional[dict]
    registro_final: Optional[dict]
    motivo_bloqueio_analise: Optional[str]
    motivo_bloqueio_risco: Optional[str]


class GrafoConfig:
    def __init__(
        self,
        llm: LLMGateway,
        logger: AgentLogger,
        pack: DomainPack | None = None,
        rag: PoliticaRAG | None = None,
    ):
        self.llm = llm
        self.logger = logger
        self.pack = pack or carregar_pack()
        self.rag = rag or PoliticaRAG(self.pack.policy_path)
        self.prompt_estruturacao: PromptAsset = self.pack.prompts["estruturacao"]
        self.prompt_risco: PromptAsset = self.pack.prompts["risco"]


def construir_grafo(config: GrafoConfig | None = None, llm: LLMGateway | None = None, logger: AgentLogger | None = None):
    if config is None:
        if llm is None or logger is None:
            raise ValueError("Informe GrafoConfig ou (llm, logger)")
        config = GrafoConfig(llm=llm, logger=logger)

    def no_agente1(estado: EstadoReclamacao) -> dict:
        analise, motivo_bloqueio = estruturacao.executar(
            estado["reclamacao"],
            config.llm,
            config.logger,
            prompt=config.prompt_estruturacao,
            rag=config.rag,
        )
        return {"analise": analise.model_dump(mode="json"), "motivo_bloqueio_analise": motivo_bloqueio}

    def rotear_risco(estado: EstadoReclamacao) -> str:
        canal = estado["reclamacao"].get("canal", "")
        return "risco_expresso" if PoliticaRAG.regra_canal_critico(canal) else "risco_completo"

    def no_risco_expresso(estado: EstadoReclamacao) -> dict:
        analise = AnaliseEstruturada.model_validate(estado["analise"])
        parecer = risco.executar_expresso(estado["reclamacao"], analise, config.logger, rag=config.rag)
        return {"parecer_risco": parecer.model_dump(mode="json"), "motivo_bloqueio_risco": None}

    def no_risco_completo(estado: EstadoReclamacao) -> dict:
        analise = AnaliseEstruturada.model_validate(estado["analise"])
        parecer, motivo_bloqueio = risco.executar_completo(
            estado["reclamacao"],
            analise,
            config.llm,
            config.logger,
            prompt=config.prompt_risco,
            rag=config.rag,
        )
        return {"parecer_risco": parecer.model_dump(mode="json"), "motivo_bloqueio_risco": motivo_bloqueio}

    def no_agente3(estado: EstadoReclamacao) -> dict:
        analise = AnaliseEstruturada.model_validate(estado["analise"])
        parecer = ParecerRisco.model_validate(estado["parecer_risco"])
        registro = consolidacao.executar(
            estado["reclamacao"],
            analise,
            parecer,
            config.logger,
            motivo_bloqueio_analise=estado.get("motivo_bloqueio_analise"),
            motivo_bloqueio_risco=estado.get("motivo_bloqueio_risco"),
        )
        return {"registro_final": registro.model_dump(mode="json")}

    grafo = StateGraph(EstadoReclamacao)
    grafo.add_node("agente_1", no_agente1)
    grafo.add_node("risco_expresso", no_risco_expresso)
    grafo.add_node("risco_completo", no_risco_completo)
    grafo.add_node("agente_3", no_agente3)

    grafo.add_edge(START, "agente_1")
    grafo.add_conditional_edges(
        "agente_1",
        rotear_risco,
        {"risco_expresso": "risco_expresso", "risco_completo": "risco_completo"},
    )
    grafo.add_edge("risco_expresso", "agente_3")
    grafo.add_edge("risco_completo", "agente_3")
    grafo.add_edge("agente_3", END)

    return grafo.compile()


def processar_reclamacao(app, reclamacao: dict) -> dict:
    estado_final = app.invoke(
        {
            "reclamacao": reclamacao,
            "analise": None,
            "parecer_risco": None,
            "registro_final": None,
            "motivo_bloqueio_analise": None,
            "motivo_bloqueio_risco": None,
        }
    )
    return estado_final["registro_final"]
