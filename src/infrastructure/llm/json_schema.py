"""Geração de JSON Schema estrito para tool-calling."""

from copy import deepcopy
from typing import Any, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def _aplicar_estrito(esquema: dict[str, Any]) -> dict[str, Any]:
    esquema = deepcopy(esquema)
    esquema.pop("title", None)

    definicoes = esquema.get("$defs", {})
    for nome, definicao in definicoes.items():
        definicoes[nome] = _aplicar_estrito(definicao)

    tipo = esquema.get("type")
    if tipo == "object":
        propriedades = esquema.get("properties", {})
        for chave, prop in propriedades.items():
            propriedades[chave] = _aplicar_estrito(prop)
            propriedades[chave].pop("title", None)
        esquema["additionalProperties"] = False
        if propriedades:
            esquema["required"] = list(propriedades.keys())

    if "items" in esquema:
        esquema["items"] = _aplicar_estrito(esquema["items"])

    for chave in ("anyOf", "oneOf", "allOf"):
        if chave in esquema:
            esquema[chave] = [_aplicar_estrito(item) for item in esquema[chave]]

    return esquema


def schema_para_tool(modelo: Type[T]) -> dict[str, Any]:
    esquema = _aplicar_estrito(modelo.model_json_schema())
    return {
        "name": f"retornar_{modelo.__name__.lower()}",
        "description": (
            f"Retorna exclusivamente um objeto JSON válido no formato {modelo.__name__}. "
            "Não inclua texto fora do JSON. Use apenas valores permitidos pelos enums do schema."
        ),
        "input_schema": esquema,
    }
