"""Agente 1 — Recepção e Estruturação.

Recebe a reclamação bruta e devolve a análise estruturada do Nível 1
(categoria, produto, sentimento, urgência, resumo), usando a política
interna como contexto via RAG. É o mesmo agente usado isoladamente no
Nível 1 e como primeiro nó do grafo no Nível 2.
"""

import time

from .. import rag
from ..llm_client import LLMClient
from ..logging_utils import AgentLogger
from ..ofuscacao import higienizar
from ..schemas import AnaliseEstruturada

NOME_AGENTE = "agente_1_estruturacao"

PROMPT_SISTEMA = """Você é um analista de reclamações de uma instituição financeira.
Classifique a reclamação do cliente de forma objetiva e consistente, usando exclusivamente
as categorias e produtos permitidos pelo schema fornecido.

Categorias possíveis: Cobrança Indevida, Atendimento, Fraude/Segurança, Produto/Serviço,
Cancelamento, Outros.
Produtos possíveis: Cartão de Crédito, Conta Corrente, Empréstimo, Investimentos, Seguros,
Não Identificado (use quando não houver evidência clara no texto).
Sentimento: Positivo, Neutro, Negativo, Crítico.
Urgência: Baixa, Média, Alta, Crítica.

Use o trecho da política interna abaixo apenas como contexto de negócio (prazos, regras por
produto/canal) para calibrar a urgência — não cite a política no resumo.

Trecho da política interna relevante:
{contexto}

O resumo deve ter 2-3 linhas, em linguagem padronizada e neutra, sem palavras impróprias e
sem repetir dados pessoais do cliente (CPF, conta, cartão)."""


def executar(reclamacao: dict, llm: LLMClient, logger: AgentLogger) -> AnaliseEstruturada:
    inicio = time.perf_counter()

    contexto = rag.buscar_contexto(
        f"{reclamacao['texto_reclamacao']} {reclamacao.get('produto') or ''} {reclamacao.get('canal', '')}"
    )
    system = PROMPT_SISTEMA.format(contexto=contexto or "(nenhum trecho relevante encontrado)")
    user = (
        f"Canal: {reclamacao.get('canal', 'não informado')}\n"
        f"Produto informado: {reclamacao.get('produto') or 'não informado'}\n"
        f"Texto da reclamação:\n{reclamacao['texto_reclamacao']}"
    )

    analise = llm.gerar_estruturado(system, user, AnaliseEstruturada)
    analise.resumo = higienizar(analise.resumo)

    duracao_ms = (time.perf_counter() - inicio) * 1000
    logger.registrar(reclamacao["id"], NOME_AGENTE, user, analise.model_dump(mode="json"), duracao_ms)
    return analise
