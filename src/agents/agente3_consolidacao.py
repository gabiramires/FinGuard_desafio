"""Agente 3 — Consolidação por reclamação.

Empacota a saída dos agentes 1 e 2 em um RegistroReclamacao. A geração do
relatório gerencial (dashboard agregando todas as reclamações) é feita à
parte, em relatorio.py, depois que todas as reclamações passam pelo grafo
— um dashboard não faz sentido por reclamação isolada, precisa do lote
inteiro (ver seção "Geração de Relatório Gerencial" do edital).
"""

import time

from ..logging_utils import AgentLogger
from ..schemas import AnaliseEstruturada, ParecerRisco, RegistroReclamacao

NOME_AGENTE = "agente_3_consolidacao"


def executar(
    reclamacao: dict,
    analise: AnaliseEstruturada,
    parecer_risco: ParecerRisco | None,
    logger: AgentLogger,
) -> RegistroReclamacao:
    inicio = time.perf_counter()

    registro = RegistroReclamacao(
        id=reclamacao["id"],
        canal=reclamacao.get("canal", ""),
        data_reclamacao=reclamacao.get("data_reclamacao"),
        texto_reclamacao=reclamacao["texto_reclamacao"],
        analise=analise,
        parecer_risco=parecer_risco,
    )

    duracao_ms = (time.perf_counter() - inicio) * 1000
    logger.registrar(
        reclamacao["id"],
        NOME_AGENTE,
        {"analise": analise.model_dump(mode="json"), "parecer_risco": parecer_risco.model_dump(mode="json") if parecer_risco else None},
        registro.model_dump(mode="json"),
        duracao_ms,
    )
    return registro
