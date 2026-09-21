"""CLI do FinGuard.

Nível 1: só o agente de estruturação (classificador) sobre cada reclamação.
Nível 2: grafo LangGraph completo (agente_1 -> agente_2 -> agente_3) com
relatório gerencial agregado.

Exemplos:
    python main.py --nivel 1 --input data/reclamacoes.csv --limit 20
    python main.py --nivel 2 --input data/reclamacoes.csv --provider mock
"""

import argparse
import time

import pandas as pd
from dotenv import load_dotenv

from src import relatorio
from src.agents import agente1_estruturacao
from src.graph import construir_grafo, processar_reclamacao
from src.llm_client import LLMClient
from src.logging_utils import AgentLogger


def carregar_reclamacoes(caminho_csv: str, limite: int | None) -> list[dict]:
    df = pd.read_csv(caminho_csv, dtype=str).fillna("")
    registros = df.to_dict(orient="records")
    for registro in registros:
        registro["produto"] = registro.get("produto") or None
    if limite:
        registros = registros[:limite]
    return registros


def rodar_nivel1(reclamacoes: list[dict], llm: LLMClient, logger: AgentLogger) -> list[dict]:
    resultados = []
    for i, reclamacao in enumerate(reclamacoes, start=1):
        print(f"[nível 1] {i}/{len(reclamacoes)} — {reclamacao['id']}")
        analise = agente1_estruturacao.executar(reclamacao, llm, logger)
        resultados.append(
            {
                "id": reclamacao["id"],
                "canal": reclamacao.get("canal", ""),
                "data_reclamacao": reclamacao.get("data_reclamacao"),
                "texto_reclamacao": reclamacao["texto_reclamacao"],
                "analise": analise.model_dump(mode="json"),
                "parecer_risco": None,
            }
        )
    return resultados


def rodar_nivel2(reclamacoes: list[dict], llm: LLMClient, logger: AgentLogger) -> list[dict]:
    app = construir_grafo(llm, logger)
    resultados = []
    for i, reclamacao in enumerate(reclamacoes, start=1):
        print(f"[nível 2] {i}/{len(reclamacoes)} — {reclamacao['id']}")
        resultados.append(processar_reclamacao(app, reclamacao))
    return resultados


def main() -> None:
    parser = argparse.ArgumentParser(description="FinGuard — análise inteligente de reclamações")
    parser.add_argument("--nivel", type=int, choices=[1, 2], default=1, help="1 = classificador; 2 = orquestrador multi-agente")
    parser.add_argument("--input", default="data/reclamacoes.csv")
    parser.add_argument("--limit", type=int, default=None, help="processa só as N primeiras linhas (útil para teste rápido)")
    parser.add_argument("--provider", default=None, help="mock | anthropic | bedrock (sobrescreve FINGUARD_LLM_PROVIDER do .env)")
    args = parser.parse_args()

    load_dotenv()

    llm = LLMClient(provider=args.provider)
    logger = AgentLogger()

    reclamacoes = carregar_reclamacoes(args.input, args.limit)
    print(f"Carregadas {len(reclamacoes)} reclamações de {args.input} (provider={llm.provider})")

    inicio = time.perf_counter()

    if args.nivel == 1:
        resultados = rodar_nivel1(reclamacoes, llm, logger)
        relatorio.exportar_json(resultados, "reports/resultados_nivel1.json")
        relatorio.exportar_csv(resultados, "reports/resultados_nivel1.csv")
        relatorio.exportar_html(resultados, "reports/relatorio_nivel1.html")
        print("Saídas: reports/resultados_nivel1.json, reports/resultados_nivel1.csv, reports/relatorio_nivel1.html")
    else:
        resultados = rodar_nivel2(reclamacoes, llm, logger)
        dashboard = relatorio.montar_dashboard(resultados)
        relatorio.exportar_json(resultados, "reports/resultados_nivel2.json")
        relatorio.exportar_csv(resultados, "reports/resultados_nivel2.csv")
        relatorio.exportar_html(resultados, "reports/relatorio_gerencial.html", dashboard)
        relatorio.exportar_markdown(dashboard, "reports/relatorio_gerencial.md")
        print(
            "Saídas: reports/resultados_nivel2.json, reports/resultados_nivel2.csv, "
            "reports/relatorio_gerencial.html, reports/relatorio_gerencial.md"
        )

    duracao = time.perf_counter() - inicio
    print(f"Concluído em {duracao:.1f}s. Logs de execução por agente em reports/logs.jsonl.")


if __name__ == "__main__":
    main()
