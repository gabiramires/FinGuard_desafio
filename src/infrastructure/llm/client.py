"""Gateway de LLM — saída estruturada via tool-calling com JSON schema estrito."""

import os
from typing import Type, TypeVar

from pydantic import BaseModel

from .json_schema import schema_para_tool
from .mock import gerar_estruturado as mock_gerar

T = TypeVar("T", bound=BaseModel)

_MOCK_MODEL_ID = "mock-heuristics-v1"

_MODELOS_SUGERIDOS = {
    "anthropic": "claude-sonnet-4-20250514",
    "bedrock": "anthropic.claude-3-5-sonnet-20241022-v2:0",
}


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
        else:
            raise ValueError(f"Provider desconhecido: {self.provider!r} (use mock, anthropic ou bedrock)")

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
                    return schema.model_validate(bloco.input)
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
                    return schema.model_validate(bloco["toolUse"]["input"])
            raise RuntimeError("Resposta do Bedrock não trouxe toolUse.")

        raise ValueError(f"Provider não suportado: {self.provider!r}")
