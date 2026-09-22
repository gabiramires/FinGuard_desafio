"""Contratos dos agentes — execução desacoplada de prompt e modelo."""

from dataclasses import dataclass
from typing import Any, Protocol, Type

from pydantic import BaseModel

from src.infrastructure.llm.client import LLMGateway
from src.infrastructure.logging.agent_logger import AgentLogger
from src.prompts.loader import PromptAsset


@dataclass(frozen=True)
class AgentRunContext:
    prompt_version: str
    prompt_hash: str
    output_model: str
    agent_id: str


class StructuredAgent(Protocol):
    agent_id: str
    prompt: PromptAsset

    def executar(self, reclamacao: dict, logger: AgentLogger) -> BaseModel: ...


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

    def executar(self, reclamacao: dict, logger: AgentLogger, **variaveis_extras: Any) -> BaseModel:
        import time

        from src.domain.models import AnaliseEstruturada

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
        resultado = self.llm.gerar_estruturado(system, user, schema)

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
        return resultado
