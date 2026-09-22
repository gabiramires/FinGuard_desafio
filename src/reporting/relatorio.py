"""Dashboard e exportadores de relatório."""

import csv
import html
import json
from collections import Counter
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

NIVEIS_CRITICOS = {"Alto", "Crítico"}


def montar_dashboard(registros: list[dict]) -> dict:
    total = len(registros)
    contagem_categoria = Counter(r["analise"]["categoria"] for r in registros)
    contagem_produto = Counter(r["analise"]["produto"] for r in registros)
    contagem_urgencia = Counter(r["analise"]["urgencia"] for r in registros)
    contagem_sentimento = Counter(r["analise"]["sentimento"] for r in registros)
    contagem_risco = Counter(
        r["parecer_risco"]["nivel_risco"] for r in registros if r.get("parecer_risco")
    )

    ordem_risco = {"Crítico": 0, "Alto": 1, "Médio": 2, "Baixo": 3}
    criticas = [
        r
        for r in registros
        if r.get("parecer_risco") and r["parecer_risco"]["nivel_risco"] in NIVEIS_CRITICOS
    ]
    criticas.sort(key=lambda r: ordem_risco.get(r["parecer_risco"]["nivel_risco"], 9))

    bloqueadas = [r for r in registros if r.get("bloqueado_seguranca")]

    return {
        "total_processado": total,
        "distribuicao_categoria": dict(contagem_categoria),
        "distribuicao_produto": dict(contagem_produto),
        "distribuicao_urgencia": dict(contagem_urgencia),
        "distribuicao_sentimento": dict(contagem_sentimento),
        "distribuicao_risco": dict(contagem_risco),
        "reclamacoes_criticas": criticas,
        "reclamacoes_bloqueadas": bloqueadas,
        "recomendacoes": gerar_recomendacoes(total, contagem_categoria, contagem_risco, len(bloqueadas)),
    }


def gerar_recomendacoes(
    total: int, contagem_categoria: Counter, contagem_risco: Counter, total_bloqueadas: int = 0
) -> list[str]:
    if total == 0:
        return ["Nenhuma reclamação processada neste lote."]

    recomendacoes = []
    if total_bloqueadas:
        recomendacoes.append(
            f"{total_bloqueadas} reclamação(ões) não puderam ser classificadas automaticamente (bloqueio "
            "de moderação do gateway ou resposta inválida do modelo) — requerem revisão manual imediata "
            "(ver seção 'Reclamações bloqueadas por segurança'; nem todo bloqueio é tentativa de ataque)."
        )

    pct_fraude = contagem_categoria.get("Fraude/Segurança", 0) / total
    if pct_fraude >= 0.15:
        recomendacoes.append(
            f"{pct_fraude:.0%} das reclamações envolvem indícios de fraude — reforçar a equipe de "
            "Prevenção a Fraudes (política interna, seção 2.4)."
        )

    criticos = contagem_risco.get("Crítico", 0)
    if criticos:
        recomendacoes.append(
            f"{criticos} reclamação(ões) em nível de risco Crítico — exigem contato ativo em até 2h "
            "e escalação a Compliance (política interna, seção 2.4)."
        )

    pct_cobranca = contagem_categoria.get("Cobrança Indevida", 0) / total
    if pct_cobranca >= 0.25:
        recomendacoes.append(
            f"{pct_cobranca:.0%} das reclamações são de cobrança indevida — investigar causa raiz "
            "recorrente junto à área de Operações."
        )

    if not recomendacoes:
        recomendacoes.append("Nenhum padrão crítico identificado no lote — manter monitoramento padrão de SLA.")

    return recomendacoes


def _adicionar_barras(fig: go.Figure, contagem: dict, row: int, col: int) -> None:
    fig.add_trace(go.Bar(x=list(contagem.keys()), y=list(contagem.values())), row=row, col=col)


def grafico_distribuicoes(dashboard: dict) -> go.Figure:
    fig = make_subplots(rows=2, cols=2, subplot_titles=("Categoria", "Produto", "Urgência", "Sentimento"))
    _adicionar_barras(fig, dashboard["distribuicao_categoria"], 1, 1)
    _adicionar_barras(fig, dashboard["distribuicao_produto"], 1, 2)
    _adicionar_barras(fig, dashboard["distribuicao_urgencia"], 2, 1)
    _adicionar_barras(fig, dashboard["distribuicao_sentimento"], 2, 2)
    fig.update_layout(
        title="FinGuard — Distribuição das Reclamações Processadas",
        showlegend=False,
        height=700,
    )
    return fig


def exportar_json(registros: list[dict], caminho: str) -> None:
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")


def exportar_csv(registros: list[dict], caminho: str) -> None:
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    campos = [
        "id", "canal", "categoria", "produto", "sentimento", "urgencia",
        "resumo", "nivel_risco", "necessita_escalacao_imediata",
        "bloqueado_seguranca", "motivo_bloqueio",
    ]
    with destino.open("w", newline="", encoding="utf-8") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=campos)
        writer.writeheader()
        for registro in registros:
            parecer = registro.get("parecer_risco") or {}
            writer.writerow({
                "id": registro["id"],
                "canal": registro["canal"],
                "categoria": registro["analise"]["categoria"],
                "produto": registro["analise"]["produto"],
                "sentimento": registro["analise"]["sentimento"],
                "urgencia": registro["analise"]["urgencia"],
                "resumo": registro["analise"]["resumo"],
                "nivel_risco": parecer.get("nivel_risco", ""),
                "necessita_escalacao_imediata": parecer.get("necessita_escalacao_imediata", ""),
                "bloqueado_seguranca": registro.get("bloqueado_seguranca", False),
                "motivo_bloqueio": registro.get("motivo_bloqueio") or "",
            })


def exportar_html(registros: list[dict], caminho: str, dashboard: dict | None = None) -> None:
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    dashboard = dashboard or montar_dashboard(registros)

    fig = grafico_distribuicoes(dashboard)
    grafico_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    linhas_criticas = "".join(
        f"<tr><td>{r['id']}</td><td>{r['canal']}</td><td>{r['analise']['categoria']}</td>"
        f"<td>{(r.get('parecer_risco') or {}).get('nivel_risco', '-')}</td>"
        f"<td>{(r.get('parecer_risco') or {}).get('justificativa', '-')}</td></tr>"
        for r in dashboard.get("reclamacoes_criticas", [])
    ) or "<tr><td colspan='5'>Nenhuma reclamação crítica/alta neste lote.</td></tr>"

    recomendacoes_html = "".join(f"<li>{r}</li>" for r in dashboard.get("recomendacoes", []))

    linhas_bloqueadas = "".join(
        f"<tr><td>{html.escape(r['id'])}</td><td>{html.escape(r['canal'])}</td>"
        f"<td>{html.escape(r.get('motivo_bloqueio') or '-')}</td></tr>"
        for r in dashboard.get("reclamacoes_bloqueadas", [])
    ) or "<tr><td colspan='3'>Nenhuma reclamação bloqueada por segurança neste lote.</td></tr>"

    html_saida = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8" />
<title>FinGuard — Relatório de Reclamações</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1a1a1a; }}
h1 {{ margin-bottom: 0.2rem; }}
.resumo {{ color: #555; margin-bottom: 1.5rem; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 0.9rem; vertical-align: top; }}
th {{ background: #f4f4f4; }}
</style>
</head>
<body>
<h1>FinGuard — Relatório de Análise de Reclamações</h1>
<p class="resumo">Total processado: {dashboard['total_processado']} reclamações.</p>
{grafico_html}
<h2>Recomendações</h2>
<ul>{recomendacoes_html}</ul>
<h2>Reclamações críticas / alto risco</h2>
<table>
<thead><tr><th>ID</th><th>Canal</th><th>Categoria</th><th>Nível de Risco</th><th>Justificativa</th></tr></thead>
<tbody>{linhas_criticas}</tbody>
</table>
<h2>Reclamações bloqueadas por segurança (revisão manual)</h2>
<table>
<thead><tr><th>ID</th><th>Canal</th><th>Motivo do bloqueio</th></tr></thead>
<tbody>{linhas_bloqueadas}</tbody>
</table>
</body>
</html>"""
    destino.write_text(html_saida, encoding="utf-8")


def exportar_markdown(dashboard: dict, caminho: str) -> None:
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)

    linhas = [
        "# FinGuard — Relatório Gerencial\n",
        f"Total processado: **{dashboard['total_processado']}** reclamações.\n",
        "## Distribuição por categoria",
        *[f"- {k}: {v}" for k, v in dashboard["distribuicao_categoria"].items()],
        "\n## Distribuição por produto",
        *[f"- {k}: {v}" for k, v in dashboard["distribuicao_produto"].items()],
        "\n## Distribuição por urgência",
        *[f"- {k}: {v}" for k, v in dashboard["distribuicao_urgencia"].items()],
        "\n## Distribuição por nível de risco",
        *[f"- {k}: {v}" for k, v in dashboard["distribuicao_risco"].items()],
        "\n## Recomendações",
        *[f"- {r}" for r in dashboard["recomendacoes"]],
        "\n## Reclamações críticas / alto risco",
    ]

    if dashboard["reclamacoes_criticas"]:
        linhas.append("| ID | Canal | Categoria | Nível de risco | Justificativa |")
        linhas.append("|---|---|---|---|---|")
        for registro in dashboard["reclamacoes_criticas"]:
            parecer = registro.get("parecer_risco") or {}
            linhas.append(
                f"| {registro['id']} | {registro['canal']} | {registro['analise']['categoria']} | "
                f"{parecer.get('nivel_risco', '-')} | {parecer.get('justificativa', '-')} |"
            )
    else:
        linhas.append("Nenhuma reclamação crítica/alta neste lote.")

    linhas.append("\n## Reclamações bloqueadas por segurança (revisão manual)")
    if dashboard.get("reclamacoes_bloqueadas"):
        linhas.append("| ID | Canal | Motivo do bloqueio |")
        linhas.append("|---|---|---|")
        for registro in dashboard["reclamacoes_bloqueadas"]:
            linhas.append(f"| {registro['id']} | {registro['canal']} | {registro.get('motivo_bloqueio', '-')} |")
    else:
        linhas.append("Nenhuma reclamação bloqueada por segurança neste lote.")

    destino.write_text("\n".join(linhas), encoding="utf-8")
