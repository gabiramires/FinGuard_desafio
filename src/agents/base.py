"""Contratos dos agentes — execução desacoplada de prompt e modelo."""

from dataclasses import dataclass
from typing import Any, Protocol, Type

from pydantic import BaseModel

from src.domain.enums import Categoria, NivelRisco, Produto, Sentimento, Urgencia
from src.domain.models import AnaliseEstruturada, ParecerRisco
from src.infrastructure.llm.client import (
    ConteudoBloqueadoError,
    LLMGateway,
    RespostaAgenteInvalidaError,
)
from src.infrastructure.logging.agent_logger import AgentLogger
from src.prompts.loader import PromptAsset


_PADROES_ATAQUE = (
    "prompt_injection",
    "attack_instruction",
    "jailbreak",
    "manipulat",
    "bypass",
    "guardrail",
    "system_prompt",
)


def _suspeita_ataque(bloqueio: RespostaAgenteInvalidaError) -> bool:
    """Só marca como tentativa de ataque quando a categoria de moderação do gateway
    realmente indica isso (prompt injection/jailbreak/etc).

    O gateway pode bloquear (finish_reason=content_filter) por outros motivos alheios a
    ataque — ex.: linguagem de sofrimento/desespero extremo em reclamações legítimas — e
    nesses casos não faz sentido rotular a reclamação como fraude/tentativa de manipulação.
    """
    if not isinstance(bloqueio, ConteudoBloqueadoError):
        return False
    texto = f"{bloqueio.motivo} {bloqueio.detalhe or ''}".lower()
    return any(padrao in texto for padrao in _PADROES_ATAQUE)


def _resultado_bloqueado(schema: Type[BaseModel], bloqueio: RespostaAgenteInvalidaError) -> BaseModel:
    """Fallback seguro quando a chamada ao LLM não produz uma saída estruturada válida.

    Motivos possíveis: (1) o gateway recusou gerar a tool call por detectar uma tentativa
    real de prompt injection/manipulação; (2) o gateway bloqueou por outro motivo de
    moderação não relacionado a ataque (ex.: sofrimento extremo do cliente); ou (3) o modelo
    devolveu um payload que não valida contra o schema (erro técnico do provider). Só o
    caso (1) é rotulado como suspeita de ataque — os demais ficam neutros, só sinalizados
    para revisão manual.
    """
    suspeita_ataque = _suspeita_ataque(bloqueio)
    if suspeita_ataque:
        explicacao = "possível tentativa de manipulação do modelo (prompt injection)"
    elif isinstance(bloqueio, ConteudoBloqueadoError):
        explicacao = "bloqueado pela moderação do gateway por motivo não relacionado a ataque"
    else:
        explicacao = "resposta do modelo inválida/mal formatada"

    if schema is AnaliseEstruturada:
        return AnaliseEstruturada(
            categoria=Categoria.FRAUDE_SEGURANCA if suspeita_ataque else Categoria.OUTROS,
            produto=Produto.NAO_IDENTIFICADO,
            sentimento=Sentimento.CRITICO if suspeita_ataque else Sentimento.NEUTRO,
            urgencia=Urgencia.CRITICA if suspeita_ataque else Urgencia.ALTA,
            resumo=(
                f"Não foi possível gerar a análise automática ({bloqueio.motivo}) — {explicacao}. "
                "Não classificado automaticamente; requer revisão manual."
            ),
        )
    if schema is ParecerRisco:
        return ParecerRisco(
            nivel_risco=NivelRisco.CRITICO if suspeita_ataque else NivelRisco.ALTO,
            justificativa=(
                f"Não foi possível gerar o parecer de risco ({bloqueio.motivo}) — {explicacao}. "
                "Escalar para revisão manual."
            ),
            indicios_fraude=suspeita_ataque,
            indicios_violacao_regulatoria=False,
            risco_reputacional=suspeita_ataque,
            necessita_escalacao_imediata=True,
        )
    raise bloqueio


@dataclass(frozen=True)
class AgentRunContext:
    prompt_version: str
    prompt_hash: str
    output_model: str
    agent_id: str


class StructuredAgent(Protocol):
    agent_id: str
    prompt: PromptAsset

    def executar(self, reclamacao: dict, logger: AgentLogger) -> tuple[BaseModel, str | None]: ...


@dataclass
class LLMStructuredAgent:
    """Agente genérico: prompt asset + gateway LLM + builder de contexto RAG."""

    prompt: PromptAsset
    llm: LLMGateway
    rag_contexto: Any
    pos_processar: Any | None = None

    @property
    def agent_id(self) -> str:
        return self.prompt.agent_id

    def _montar_variaveis(self, reclamacao: dict, **extras: Any) -> dict[str, Any]:
        return {
            "canal": reclamacao.get("canal", ""),
            "produto": reclamacao.get("produto") or "não informado",
            "texto_reclamacao": reclamacao["texto_reclamacao"],
            **extras,
        }

    def executar(self, reclamacao: dict, logger: AgentLogger, **variaveis_extras: Any) -> tuple[BaseModel, str | None]:
        import time

        inicio = time.perf_counter()
        contexto = self.rag_contexto(reclamacao, **variaveis_extras)

        extras_render = dict(variaveis_extras)
        analise = extras_render.pop("analise", None)
        if isinstance(analise, AnaliseEstruturada):
            extras_render.update(
                {
                    "categoria": analise.categoria.value,
                    "produto": analise.produto.value,
                    "sentimento": analise.sentimento.value,
                    "urgencia": analise.urgencia.value,
                    "resumo": analise.resumo,
                }
            )

        variaveis = self._montar_variaveis(
            reclamacao,
            contexto=contexto or "(nenhum trecho relevante encontrado)",
            **extras_render,
        )
        system, user = self.prompt.render(**variaveis)
        schema: Type[BaseModel] = self.prompt.output_model
        motivo_bloqueio: str | None = None
        try:
            resultado = self.llm.gerar_estruturado(system, user, schema)
        except RespostaAgenteInvalidaError as bloqueio:
            print(f"[aviso] {reclamacao['id']}: {bloqueio} — usando fallback para revisão manual")
            motivo_bloqueio = f"{bloqueio.motivo}: {bloqueio.detalhe or 'sem detalhe'}"
            resultado = _resultado_bloqueado(schema, bloqueio)

        if self.pos_processar:
            resultado = self.pos_processar(resultado)

        duracao_ms = (time.perf_counter() - inicio) * 1000
        logger.registrar(
            reclamacao["id"],
            self.agent_id,
            user,
            resultado.model_dump(mode="json"),
            duracao_ms,
            prompt_version=self.prompt.version,
            output_model=self.prompt.output_model_name,
        )
        return resultado, motivo_bloqueio
