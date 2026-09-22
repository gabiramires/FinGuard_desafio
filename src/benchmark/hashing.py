"""Hashes canônicos para reprodutibilidade de benchmark."""

import hashlib
import json
import unicodedata
from typing import Any


def sha256(valor: str | bytes) -> str:
    if isinstance(valor, str):
        valor = valor.encode("utf-8")
    return hashlib.sha256(valor).hexdigest()


def canonical_text(valor: str) -> str:
    texto = valor.replace("\ufeff", "")
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    linhas = []
    for linha in texto.split("\n"):
        linha = " ".join(linha.split())
        linhas.append(linha.strip())
    return "\n".join(linhas).strip()


def text_hash(valor: str) -> str:
    return sha256(canonical_text(valor))


def canonical_json(valor: Any) -> str:
    return json.dumps(valor, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def config_hash(config: dict[str, Any]) -> str:
    return sha256(canonical_json(config))
