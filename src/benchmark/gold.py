"""Carregamento de labels gold para comparação determinística."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.benchmark.hashing import sha256, text_hash


@dataclass(frozen=True)
class GoldLabel:
    sample_id: str
    source_text_hash: str
    category: str
    product: str
    sentiment: str
    urgency: str
    risk: str
    channel: str
    schema_version: str


def carregar_gold(caminho: str | Path) -> dict[str, GoldLabel]:
    caminho = Path(caminho)
    df = pd.read_csv(caminho, dtype=str, encoding="utf-8-sig").fillna("")
    labels: dict[str, GoldLabel] = {}
    for _, linha in df.iterrows():
        label = GoldLabel(
            sample_id=linha["sample_id"],
            source_text_hash=linha["source_text_hash"],
            category=linha["category"],
            product=linha["product"],
            sentiment=linha["sentiment"],
            urgency=linha["urgency"],
            risk=linha["risk"],
            channel=linha.get("channel", ""),
            schema_version=linha.get("schema_version", ""),
        )
        labels[label.sample_id] = label
    return labels


def hash_arquivo_gold(caminho: str | Path) -> str:
    return sha256(Path(caminho).read_bytes())
