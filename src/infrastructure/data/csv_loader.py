"""Carregamento de CSV de reclamações."""

import pandas as pd


def carregar_reclamacoes(caminho_csv: str, limite: int | None = None) -> list[dict]:
    df = pd.read_csv(caminho_csv, dtype=str, encoding="utf-8-sig").fillna("")
    registros = df.to_dict(orient="records")
    for registro in registros:
        registro["produto"] = registro.get("produto") or None
    if limite:
        registros = registros[:limite]
    return registros
