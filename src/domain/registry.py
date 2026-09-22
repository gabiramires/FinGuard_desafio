"""Registro de modelos de saída referenciados pelos prompts."""

from typing import Type

from pydantic import BaseModel

from .models import AnaliseEstruturada, ParecerRisco, RegistroReclamacao

OUTPUT_MODELS: dict[str, Type[BaseModel]] = {
    "AnaliseEstruturada": AnaliseEstruturada,
    "ParecerRisco": ParecerRisco,
    "RegistroReclamacao": RegistroReclamacao,
}


def resolver_output_model(nome: str) -> Type[BaseModel]:
    try:
        return OUTPUT_MODELS[nome]
    except KeyError as exc:
        modelos = ", ".join(sorted(OUTPUT_MODELS))
        raise ValueError(f"Modelo de saída desconhecido: {nome!r}. Disponíveis: {modelos}") from exc
