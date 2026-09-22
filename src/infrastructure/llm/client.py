"""Gateway de LLM — saída estruturada via tool-calling com JSON schema estrito."""

import os
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from .json_schema import schema_para_tool
from .mock import gerar_estruturado as mock_gerar

T = TypeVar("T", bound=BaseModel)


class RespostaAgenteInvalidaError(RuntimeError):
    """Base: o provider não devolveu uma saída estruturada válida para o schema pedido."""

    def __init__(self, motivo: str, detalhe: str | None = None):
        self.motivo = motivo
        self.detalhe = detalhe
        super().__init__(f"{motivo}: {detalhe or ''}".strip())


class ConteudoBloqueadoError(RespostaAgenteInvalidaError):
    """Gateway recusou gerar a tool call (moderação/guardrail), em vez de erro de integração."""


class RespostaInvalidaError(RespostaAgenteInvalidaError):
    """Modelo devolveu uma tool call cujos argumentos não validam contra o schema esperado
    (payload corrompido/mal formatado) — visto em respostas via gateway/Bedrock."""

    def __init__(self, detalhe: str):
        super().__init__("schema_invalido", detalhe)


def _validar_schema(schema: Type[T], dados: dict) -> T:
    try:
        return schema.model_validate(dados)
    except ValidationError as exc:
        resumo = "; ".join(
            f"{'.'.join(str(p) for p in erro['loc'])}: {erro['msg']}" for erro in exc.errors()
        )
        raise RespostaInvalidaError(resumo) from exc


_MOCK_MODEL_ID = "mock-heuristics-v1"

_MODELOS_SUGERIDOS = {
    "anthropic": "claude-haiku-4-5",
    "bedrock": "anthropic.claude-haiku-4-5-20251001-v1:0",
    "litellm": "bedrock-anthropic-claude-haiku-4-5",
}

_LITELLM_BASE_URL_PADRAO = "https://dx-ai-gateway.platform.sbox.zupcloud.corp"


def resolver_modelo(provider: str, model: str | None = None) -> str:
    """Resolve o model id: CLI/env explícito > mock id > sugestão por provider."""
    explicito = (model or os.getenv("FINGUARD_LLM_MODEL") or "").strip()
    if explicito:
        return explicito
    if provider == "mock":
        return _MOCK_MODEL_ID
    sugerido = _MODELOS_SUGERIDOS.get(provider)
    if sugerido:
        return sugerido
    raise ValueError(
        f"Provider {provider!r} requer --model ou FINGUARD_LLM_MODEL "
        f"(sugestões: {', '.join(f'{k}={v}' for k, v in _MODELOS_SUGERIDOS.items())})"
    )


class LLMGateway:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = provider or os.getenv("FINGUARD_LLM_PROVIDER", "mock")
        self.model = resolver_modelo(self.provider, model)
        self._client = None

        if self.provider == "mock":
            return
        if self.provider == "anthropic":
            import anthropic

            self._client = anthropic.Anthropic()
        elif self.provider == "bedrock":
            import boto3

            self._client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
        elif self.provider == "litellm":
            from openai import DefaultHttpxClient, OpenAI

            token = os.getenv("LITELLM_TOKEN")
            if not token:
                raise ValueError("Provider 'litellm' requer LITELLM_TOKEN no ambiente/.env")
            self._client = OpenAI(
                api_key=token,
                base_url=os.getenv("LITELLM_BASE_URL", _LITELLM_BASE_URL_PADRAO),
                # verify=False: sandbox do desafio usa certificado próprio (ver doc do AI Gateway)
                http_client=DefaultHttpxClient(verify=False),
            )
        else:
            raise ValueError(f"Provider desconhecido: {self.provider!r} (use mock, anthropic, bedrock ou litellm)")

    def gerar_estruturado(self, system: str, user: str, schema: Type[T]) -> T:
        if self.provider == "mock":
            return mock_gerar(user, schema)

        tool = schema_para_tool(schema)

        if self.provider == "anthropic":
            resposta = self._client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user}],
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
            )
            for bloco in resposta.content:
                if bloco.type == "tool_use":
                    return _validar_schema(schema, bloco.input)
            raise RuntimeError("Resposta da Anthropic não trouxe tool_use.")

        if self.provider == "bedrock":
            resposta = self._client.converse(
                modelId=self.model,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": user}]}],
                toolConfig={
                    "tools": [
                        {
                            "toolSpec": {
                                "name": tool["name"],
                                "description": tool["description"],
                                "inputSchema": {"json": tool["input_schema"]},
                            }
                        }
                    ],
                    "toolChoice": {"tool": {"name": tool["name"]}},
                },
            )
            for bloco in resposta["output"]["message"]["content"]:
                if "toolUse" in bloco:
                    return _validar_schema(schema, bloco["toolUse"]["input"])
            raise RuntimeError("Resposta do Bedrock não trouxe toolUse.")

        if self.provider == "litellm":
            import json as _json

            resposta = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool["description"],
                            "parameters": tool["input_schema"],
                        },
                    }
                ],
                tool_choice={"type": "function", "function": {"name": tool["name"]}},
            )
            escolha = resposta.choices[0]
            chamadas = escolha.message.tool_calls
            if not chamadas:
                raise ConteudoBloqueadoError(escolha.finish_reason or "desconhecido", escolha.message.content)
            try:
                argumentos = _json.loads(chamadas[0].function.arguments)
            except _json.JSONDecodeError as exc:
                raise RespostaInvalidaError(f"JSON malformado: {exc}") from exc
            return _validar_schema(schema, argumentos)

        raise ValueError(f"Provider não suportado: {self.provider!r}")
