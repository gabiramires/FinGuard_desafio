"""Compatibilidade — alias para LLMGateway."""

from src.infrastructure.llm.client import LLMGateway

LLMClient = LLMGateway

__all__ = ["LLMClient", "LLMGateway"]
