"""Entidade de entrada — reclamação bruta do CSV."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Reclamacao:
    id: str
    canal: str
    texto_reclamacao: str
    data_reclamacao: str | None = None
    produto: str | None = None
    status: str | None = None

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> "Reclamacao":
        return cls(
            id=dados["id"],
            canal=dados.get("canal", ""),
            texto_reclamacao=dados["texto_reclamacao"],
            data_reclamacao=dados.get("data_reclamacao") or None,
            produto=dados.get("produto") or None,
            status=dados.get("status") or None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "canal": self.canal,
            "texto_reclamacao": self.texto_reclamacao,
            "data_reclamacao": self.data_reclamacao,
            "produto": self.produto,
            "status": self.status,
        }
