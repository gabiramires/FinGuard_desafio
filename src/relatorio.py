"""Compatibilidade — reexporta relatórios."""

from src.reporting.relatorio import (
    exportar_csv,
    exportar_html,
    exportar_json,
    exportar_markdown,
    gerar_recomendacoes,
    grafico_distribuicoes,
    montar_dashboard,
)

__all__ = [
    "exportar_csv",
    "exportar_html",
    "exportar_json",
    "exportar_markdown",
    "gerar_recomendacoes",
    "grafico_distribuicoes",
    "montar_dashboard",
]
