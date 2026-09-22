"""Log de execução por agente (rastreabilidade)."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class AgentLogger:
    def __init__(self, caminho: str = "reports/logs.jsonl"):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)

    def registrar(
        self,
        reclamacao_id: str,
        agente: str,
        entrada: Any,
        saida: Any,
        duracao_ms: float,
        *,
        prompt_version: str | None = None,
        output_model: str | None = None,
    ) -> None:
        registro = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "reclamacao_id": reclamacao_id,
            "agente": agente,
            "prompt_version": prompt_version,
            "output_model": output_model,
            "entrada": entrada,
            "saida": saida,
            "duracao_ms": round(duracao_ms, 2),
        }
        with self.caminho.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
