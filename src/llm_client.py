"""Cliente de LLM trocável entre providers.

Cada agente pede saída estruturada passando um schema pydantic; o cliente
força o modelo a responder via tool-calling com o JSON schema do modelo,
e valida a resposta com o próprio pydantic (sem parsing manual de texto).

Providers suportados (env FINGUARD_LLM_PROVIDER):
- "mock": heurísticas locais, sem custo, sem chave (default). Ver mock_llm.py.
- "anthropic": API da Anthropic (requer ANTHROPIC_API_KEY).
- "bedrock": Amazon Bedrock via boto3 (requer credenciais AWS configuradas).

Cost awareness: nada impede instanciar dois LLMClient com modelos
diferentes por agente (ex.: modelo menor no agente 1, maior no agente 2) —
ver main.py e o critério bônus de otimização de custo do edital.
"""

import os
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

_MODELOS_DEFAULT = {
    "anthropic": "claude-sonnet-5",
    "bedrock": "anthropic.claude-3-5-sonnet-20241022-v2:0",
}


def _schema_para_tool(schema: Type[BaseModel]) -> dict:
    esquema = schema.model_json_schema()
    esquema.pop("title", None)
    for propriedade in esquema.get("properties", {}).values():
        propriedade.pop("title", None)
    return {
        "name": f"retornar_{schema.__name__.lower()}",
        "description": f"Registra os dados estruturados no formato {schema.__name__}.",
        "input_schema": esquema,
    }


class LLMClient:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = provider or os.getenv("FINGUARD_LLM_PROVIDER", "mock")
        self.model = model or os.getenv("FINGUARD_LLM_MODEL") or _MODELOS_DEFAULT.get(self.provider)
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
            from . import mock_llm

            return mock_llm.gerar(system, user, schema)

        tool = _schema_para_tool(schema)

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
