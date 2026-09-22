"""Agente de consolidação por reclamação."""

import time

from src.domain.models import AnaliseEstruturada, ParecerRisco, RegistroReclamacao
from src.infrastructure.logging.agent_logger import AgentLogger

NOME_AGENTE = "agente_3_consolidacao"


def executar(
    reclamacao: dict,
    analise: AnaliseEstruturada,
    parecer_risco: ParecerRisco | None,
    logger: AgentLogger,
    *,
    motivo_bloqueio_analise: str | None = None,
    motivo_bloqueio_risco: str | None = None,
) -> RegistroReclamacao:
    inicio = time.perf_counter()

    motivos = []
    if motivo_bloqueio_analise:
        motivos.append(f"estruturação: {motivo_bloqueio_analise}")
    if motivo_bloqueio_risco and motivo_bloqueio_risco != motivo_bloqueio_analise:
        motivos.append(f"risco: {motivo_bloqueio_risco}")

    registro = RegistroReclamacao(
        id=reclamacao["id"],
        canal=reclamacao.get("canal", ""),
        data_reclamacao=reclamacao.get("data_reclamacao"),
        texto_reclamacao=reclamacao["texto_reclamacao"],
        analise=analise,
        parecer_risco=parecer_risco,
        bloqueado_seguranca=bool(motivos),
        motivo_bloqueio=" | ".join(motivos) or None,
    )

    duracao_ms = (time.perf_counter() - inicio) * 1000
    logger.registrar(
        reclamacao["id"],
        NOME_AGENTE,
        {
            "analise": analise.model_dump(mode="json"),
            "parecer_risco": parecer_risco.model_dump(mode="json") if parecer_risco else None,
        },
        registro.model_dump(mode="json"),
        duracao_ms,
        prompt_version="n/a",
        output_model="RegistroReclamacao",
    )
    return registro
