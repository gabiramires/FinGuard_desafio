"""Orquestração de benchmark por run."""

import json
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.application.pipeline import PipelineContext, criar_contexto, rodar_nivel1, rodar_nivel2
from src.benchmark.evaluator import avaliar_contra_gold
from src.benchmark.gold import carregar_gold, hash_arquivo_gold
from src.benchmark.hashing import config_hash, sha256
from src.infrastructure.data.csv_loader import carregar_reclamacoes
from src.infrastructure.llm.client import LLMGateway
from src.infrastructure.logging.agent_logger import AgentLogger
from src.prompts.loader import carregar_pack, prompt_hash_conjunto
from src.reporting import relatorio


@dataclass
class BenchmarkConfig:
    nivel: int
    input_csv: str
    output_dir: str = "reports/benchmarks"
    limit: int | None = None
    provider: str | None = None
    model: str | None = None
    gold_path: str | None = None
    pack_path: str | None = None
    max_workers: int = 1


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _git_status() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "status", "--porcelain"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip() or "clean"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _escrever_json(caminho: Path, dados: dict[str, Any]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def _atualizar_checkpoint(caminho: Path, status: str, processed: int, total: int, erro: str | None = None) -> None:
    payload: dict[str, Any] = {
        "status": status,
        "processed": processed,
        "total": total,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if erro:
        payload["error"] = erro
    _escrever_json(caminho, payload)


def _dataset_hash(caminho: str) -> str:
    return sha256(Path(caminho).read_bytes())


def executar_benchmark(config: BenchmarkConfig) -> Path:
    run_id = str(uuid.uuid4())
    run_dir = Path(config.output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    pack = carregar_pack(Path(config.pack_path) if config.pack_path else None)
    llm = LLMGateway(provider=config.provider, model=config.model)
    logger = AgentLogger(str(run_dir / "logs.jsonl"))
    ctx = criar_contexto(llm, logger, pack)

    checkpoint_path = run_dir / "benchmark_checkpoint.json"
    total = len(carregar_reclamacoes(config.input_csv, config.limit))
    _atualizar_checkpoint(checkpoint_path, "running", 0, total)

    inicio = time.perf_counter()
    status = "completed"
    erro: str | None = None
    resultados: list[dict] = []

    try:
        reclamacoes = carregar_reclamacoes(config.input_csv, config.limit)
        if config.nivel == 1:
            resultados = rodar_nivel1(ctx, reclamacoes, max_workers=config.max_workers)
        else:
            resultados = rodar_nivel2(ctx, reclamacoes, max_workers=config.max_workers)
        _atualizar_checkpoint(checkpoint_path, "completed", len(resultados), total)
    except Exception as exc:  # noqa: BLE001 — benchmark must capture failure
        status = "failed"
        erro = str(exc)
        _atualizar_checkpoint(checkpoint_path, "failed", len(resultados), total, erro=erro)
        raise
    finally:
        duracao_s = time.perf_counter() - inicio

    _persistir_saidas(run_dir, config, resultados, ctx, status, duracao_s, erro)
    return run_dir


def _persistir_saidas(
    run_dir: Path,
    config: BenchmarkConfig,
    resultados: list[dict],
    ctx: PipelineContext,
    status: str,
    duracao_s: float,
    erro: str | None,
) -> None:
    pack = ctx.pack
    prompt_hashes = {papel: prompt.content_hash for papel, prompt in pack.prompts.items()}
    prompt_versions = {papel: prompt.version for papel, prompt in pack.prompts.items()}

    pipeline_config = {
        "nivel": config.nivel,
        "provider": ctx.llm.provider,
        "model": ctx.llm.model,
        "pack_version": pack.version,
        "prompt_versions": prompt_versions,
        "input_csv": config.input_csv,
        "limit": config.limit,
    }

    cfg_hash = config_hash(
        {
            "pipeline": pipeline_config,
            "pack_hash": pack.pack_hash,
            "prompt_hash": prompt_hash_conjunto(pack),
            "dataset_hash": _dataset_hash(config.input_csv),
            "gold_hash": hash_arquivo_gold(config.gold_path) if config.gold_path else None,
        }
    )

    benchmark_run = {
        "id": run_dir.name,
        "status": status,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "duration_s": round(duracao_s, 2),
        "git_commit": _git_commit(),
        "git_status": _git_status(),
        "decision_model": ctx.llm.provider,
        "model": ctx.llm.model,
        "pack_version": pack.version,
        "pack_hash": pack.pack_hash,
        "prompt_hash": prompt_hash_conjunto(pack),
        "prompt_versions": prompt_versions,
        "prompt_hashes": prompt_hashes,
        "config_hash": cfg_hash,
        "pipeline_config": pipeline_config,
        "dataset_hash": _dataset_hash(config.input_csv),
        "error": erro,
    }

    if config.gold_path:
        benchmark_run["gold_path"] = config.gold_path
        benchmark_run["gold_hash"] = hash_arquivo_gold(config.gold_path)

    _escrever_json(run_dir / "benchmark_run.json", benchmark_run)

    executions_path = run_dir / "sample_executions.jsonl"
    with executions_path.open("w", encoding="utf-8") as arquivo:
        for resultado in resultados:
            linha = {
                "runId": run_dir.name,
                "sampleId": resultado["id"],
                "category": resultado["analise"]["categoria"],
                "product": resultado["analise"]["produto"],
                "sentiment": resultado["analise"]["sentimento"],
                "urgency": resultado["analise"]["urgencia"],
                "risk": (resultado.get("parecer_risco") or {}).get("nivel_risco"),
                "dataClass": "report_public",
            }
            arquivo.write(json.dumps(linha, ensure_ascii=False) + "\n")

    relatorio.exportar_json(resultados, str(run_dir / "resultados.json"))
    relatorio.exportar_csv(resultados, str(run_dir / "resultados.csv"))

    if config.nivel == 1:
        relatorio.exportar_html(resultados, str(run_dir / "relatorio.html"))
    else:
        dashboard = relatorio.montar_dashboard(resultados)
        relatorio.exportar_html(resultados, str(run_dir / "relatorio_gerencial.html"), dashboard)
        relatorio.exportar_markdown(dashboard, str(run_dir / "relatorio_gerencial.md"))

    if config.gold_path:
        gold = carregar_gold(config.gold_path)
        analise = avaliar_contra_gold(resultados, gold, nivel=config.nivel)
        analise["run_id"] = run_dir.name
        analise["config_hash"] = cfg_hash
        _escrever_json(run_dir / "benchmark_analysis.json", analise)
