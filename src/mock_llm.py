"""Compatibilidade — reexporta mock provider."""

from typing import Type, TypeVar

from pydantic import BaseModel

from src.infrastructure.llm.mock import gerar_estruturado

T = TypeVar("T", bound=BaseModel)


def gerar(system: str, user: str, schema: Type[T]) -> T:
    del system
    return gerar_estruturado(user, schema)


__all__ = ["gerar"]
