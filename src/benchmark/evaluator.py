"""Avaliação determinística contra gold labels."""

from collections import Counter, defaultdict
from typing import Any

from src.benchmark.gold import GoldLabel
from src.benchmark.hashing import text_hash


CAMPOS_NIVEL1 = ("category", "product", "sentiment", "urgency")
CAMPOS_NIVEL2 = (*CAMPOS_NIVEL1, "risk")

MAPEAMENTO_PREDICAO = {
    "category": lambda r: r["analise"]["categoria"],
    "product": lambda r: r["analise"]["produto"],
    "sentiment": lambda r: r["analise"]["sentimento"],
    "urgency": lambda r: r["analise"]["urgencia"],
    "risk": lambda r: (r.get("parecer_risco") or {}).get("nivel_risco"),
}


def _valor_gold(label: GoldLabel, campo: str) -> str:
    return getattr(label, campo)


def avaliar_contra_gold(
    resultados: list[dict],
    gold: dict[str, GoldLabel],
    *,
    nivel: int,
) -> dict[str, Any]:
    campos = CAMPOS_NIVEL1 if nivel == 1 else CAMPOS_NIVEL2
    ids_pred = {r["id"] for r in resultados}
    ids_gold = set(gold.keys())

    hash_mismatches: list[dict[str, str]] = []
    amostras: list[dict[str, Any]] = []

    for resultado in resultados:
        sample_id = resultado["id"]
        label = gold.get(sample_id)
        if not label:
            continue

        hash_calculado = text_hash(resultado["texto_reclamacao"])
        if hash_calculado != label.source_text_hash:
            hash_mismatches.append(
                {
                    "sample_id": sample_id,
                    "expected": label.source_text_hash,
                    "actual": hash_calculado,
                }
            )

        comparacoes = {}
        for campo in campos:
            predito = MAPEAMENTO_PREDICAO[campo](resultado)
            esperado = _valor_gold(label, campo)
            comparacoes[campo] = {
                "expected": esperado,
                "predicted": predito,
                "match": predito == esperado,
            }

        amostras.append({"sample_id": sample_id, "fields": comparacoes})

    agreement: dict[str, dict[str, Any]] = {}
    confusion: dict[str, dict[str, dict[str, int]]] = {}

    for campo in campos:
        comparados = 0
        acertos = 0
        matriz: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for amostra in amostras:
            info = amostra["fields"].get(campo)
            if not info or info["predicted"] is None:
                continue
            comparados += 1
            if info["match"]:
                acertos += 1
            matriz[info["expected"]][info["predicted"]] += 1

        agreement[campo] = {
            "compared": comparados,
            "matches": acertos,
            "rate": round(acertos / comparados, 4) if comparados else None,
        }
        confusion[campo] = {k: dict(v) for k, v in matriz.items()}

    return {
        "report_type": "benchmark_comparison",
        "reference_type": "ai_draft_non_gold",
        "nivel": nivel,
        "coverage": {
            "labels": len(gold),
            "predictions": len(resultados),
            "matched": len(amostras),
            "missing_in_predictions": sorted(ids_gold - ids_pred),
            "extra_in_predictions": sorted(ids_pred - ids_gold),
            "hash_mismatches": hash_mismatches,
        },
        "agreement": agreement,
        "confusion": confusion,
    }
