"""CLI do FinGuard.

Nível 1: classificador (agente de estruturação).
Nível 2: orquestrador multi-agente (LangGraph).
Benchmark: run rastreável com hashes, prompts versionados e comparação gold opcional.
"""

import argparse
import time
from pathlib import Path

from dotenv import load_dotenv

from src.application.pipeline import criar_contexto, rodar_nivel1, rodar_nivel2
from src.benchmark.runner import BenchmarkConfig, executar_benchmark
from src.infrastructure.data.csv_loader import carregar_reclamacoes
from src.infrastructure.llm.client import LLMGateway
from src.infrastructure.logging.agent_logger import AgentLogger
from src.prompts.loader import carregar_pack
from src.reporting import relatorio


def main() -> None:
    parser = argparse.ArgumentParser(description="FinGuard — análise inteligente de reclamações")
    parser.add_argument("--nivel", type=int, choices=[1, 2], default=1, help="1 = classificador; 2 = orquestrador multi-agente")
    parser.add_argument("--input", default="data/reclamacoes.csv")
    parser.add_argument("--limit", type=int, default=None, help="processa só as N primeiras linhas")
    parser.add_argument("--provider", default=None, help="mock | anthropic | bedrock")
    parser.add_argument(
        "--model",
        default=None,
        help="model id do provider (ex.: claude-sonnet-4-20250514). Sobrescreve FINGUARD_LLM_MODEL",
    )
    parser.add_argument("--benchmark", action="store_true", help="executa como benchmark rastreável em reports/benchmarks/<run_id>/")
    parser.add_argument("--gold", default=None, help="CSV gold para comparação determinística (ex.: data/gold/labels-ai-draft-v2.csv)")
    parser.add_argument("--pack", default=None, help="caminho alternativo para assets/pack.yaml")
    args = parser.parse_args()

    load_dotenv()

    gold_path = args.gold
    if gold_path is None and args.benchmark:
        pack = carregar_pack(Path(args.pack) if args.pack else None)
        if pack.gold_path and pack.gold_path.exists():
            gold_path = str(pack.gold_path)

    if args.benchmark:
        run_dir = executar_benchmark(
            BenchmarkConfig(
                nivel=args.nivel,
                input_csv=args.input,
                limit=args.limit,
                provider=args.provider,
                model=args.model,
                gold_path=gold_path,
                pack_path=args.pack,
            )
        )
        print(f"Benchmark concluído: {run_dir}")
        print(f"  metadata: {run_dir / 'benchmark_run.json'}")
        print(f"  execuções: {run_dir / 'sample_executions.jsonl'}")
        if gold_path:
            print(f"  análise gold: {run_dir / 'benchmark_analysis.json'}")
        return

    llm = LLMGateway(provider=args.provider, model=args.model)
    logger = AgentLogger()
    ctx = criar_contexto(llm, logger, carregar_pack(Path(args.pack) if args.pack else None))

    reclamacoes = carregar_reclamacoes(args.input, args.limit)
    print(
        f"Carregadas {len(reclamacoes)} reclamações de {args.input} "
        f"(provider={llm.provider}, model={llm.model})"
    )

    inicio = time.perf_counter()

    if args.nivel == 1:
        resultados = rodar_nivel1(ctx, reclamacoes)
        relatorio.exportar_json(resultados, "reports/resultados_nivel1.json")
        relatorio.exportar_csv(resultados, "reports/resultados_nivel1.csv")
        relatorio.exportar_html(resultados, "reports/relatorio_nivel1.html")
        print("Saídas: reports/resultados_nivel1.json, reports/resultados_nivel1.csv, reports/relatorio_nivel1.html")
    else:
        resultados = rodar_nivel2(ctx, reclamacoes)
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
    print(f"Concluído em {duracao:.1f}s. Logs em reports/logs.jsonl.")


if __name__ == "__main__":
    main()
