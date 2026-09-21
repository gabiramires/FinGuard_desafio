"""Orquestração do Nível 2 com LangGraph.

Estrutura mínima pedida no edital (start -> agente_1 -> agente_2 -> agente_3
-> end), com uma extensão de roteamento condicional depois do agente_1:
reclamações de canal Banco Central/Procon já têm o risco determinado por
regra de negócio (política 4.3) e seguem para o caminho expresso (sem LLM);
as demais passam pela análise de risco completa via LLM.
"""

from typing import Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from . import rag
from .agents import agente1_estruturacao, agente2_risco, agente3_consolidacao
from .llm_client import LLMClient
from .logging_utils import AgentLogger


class EstadoReclamacao(TypedDict):
    reclamacao: dict
    analise: Optional[dict]
    parecer_risco: Optional[dict]
    registro_final: Optional[dict]


def construir_grafo(llm: LLMClient, logger: AgentLogger):
    def no_agente1(estado: EstadoReclamacao) -> dict:
        analise = agente1_estruturacao.executar(estado["reclamacao"], llm, logger)
        return {"analise": analise.model_dump(mode="json")}

    def rotear_risco(estado: EstadoReclamacao) -> str:
        canal = estado["reclamacao"].get("canal", "")
        return "risco_expresso" if rag.regra_canal_critico(canal) else "risco_completo"

    def no_risco_expresso(estado: EstadoReclamacao) -> dict:
        from .schemas import AnaliseEstruturada

        analise = AnaliseEstruturada.model_validate(estado["analise"])
        parecer = agente2_risco.executar_expresso(estado["reclamacao"], analise, logger)
        return {"parecer_risco": parecer.model_dump(mode="json")}

    def no_risco_completo(estado: EstadoReclamacao) -> dict:
        from .schemas import AnaliseEstruturada

        analise = AnaliseEstruturada.model_validate(estado["analise"])
        parecer = agente2_risco.executar_completo(estado["reclamacao"], analise, llm, logger)
        return {"parecer_risco": parecer.model_dump(mode="json")}

    def no_agente3(estado: EstadoReclamacao) -> dict:
        from .schemas import AnaliseEstruturada, ParecerRisco

        analise = AnaliseEstruturada.model_validate(estado["analise"])
        parecer = ParecerRisco.model_validate(estado["parecer_risco"])
        registro = agente3_consolidacao.executar(estado["reclamacao"], analise, parecer, logger)
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
        {"reclamacao": reclamacao, "analise": None, "parecer_risco": None, "registro_final": None}
    )
    return estado_final["registro_final"]
