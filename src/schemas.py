"""Compatibilidade — reexporta modelos do domínio."""

from src.domain.enums import Categoria, NivelRisco, Produto, Sentimento, Urgencia
from src.domain.models import AnaliseEstruturada, ParecerRisco, RegistroReclamacao

__all__ = [
    "AnaliseEstruturada",
    "Categoria",
    "NivelRisco",
    "ParecerRisco",
    "Produto",
    "RegistroReclamacao",
    "Sentimento",
    "Urgencia",
]
