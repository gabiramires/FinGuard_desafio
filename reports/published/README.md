# Benchmarks publicados

Artefatos versionados de runs de benchmark para apresentação e reprodutibilidade.
Runs intermediários e logs completos continuam em `reports/benchmarks/` (gitignored).

## Runs

| Run ID | Nível | Amostras | Provider | Apresentação |
|---|---|---:|---|---|
| `0313a572-1a71-4a33-8608-4ab57100209a` | 2 | 500 | anthropic / claude-haiku-4-5 | [benchmark_apresentacao.html](0313a572-1a71-4a33-8608-4ab57100209a/benchmark_apresentacao.html) |

### Conteúdo por run

- `benchmark_apresentacao.html` — dashboard visual do benchmark
- `benchmark_run.json` — metadados do run (provider, prompts, hashes)
- `benchmark_analysis.json` — concordância vs gold e matrizes de confusão
- `benchmark_checkpoint.json` — status e contagem processada
- `resultados.json` / `resultados.csv` — saída por reclamação
- `relatorio_gerencial.html` — relatório gerencial do lote
