"""Compatibilidade — reexporta ofuscação."""

from src.shared.ofuscacao import higienizar, mascarar_dados_pessoais, ofuscar_palavroes

__all__ = ["higienizar", "mascarar_dados_pessoais", "ofuscar_palavroes"]
