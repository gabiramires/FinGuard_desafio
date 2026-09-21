"""Log de execução dos agentes — requisito de rastreabilidade do Nível 2.

Grava uma linha JSONL por chamada de agente: reclamação, agente, entrada,
saída e duração. Permite reconstruir, para qualquer reclamação, em qual
agente ela passou e quanto tempo cada etapa levou.
"""

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
    ) -> None:
        registro = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "reclamacao_id": reclamacao_id,
            "agente": agente,
            "entrada": entrada,
            "saida": saida,
            "duracao_ms": round(duracao_ms, 2),
        }
        with self.caminho.open("a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
