"""Higienização determinística do resumo antes de sair do sistema.

Aplicado depois do LLM (nunca confiamos no modelo pra isso): ofusca
palavras impróprias e mascara dados pessoais (CPF, cartão, conta) que
eventualmente tenham vazado do texto original da reclamação para o
resumo. Requisito de negócio: política interna (seção 5) proíbe dado
pessoal em relatório gerencial; edital do desafio exige palavrão ofuscado.
"""

import re

PALAVRAS_IMPROPRIAS = [
    "merda", "porra", "caralho", "puta", "putaria", "foda", "fodido", "fodendo",
    "cacete", "buceta", "cu", "piranha", "corno", "imbecil", "idiota", "burro",
    "estupido", "estúpido", "arrombado", "desgraca", "desgraça", "bosta",
    "maldito", "cretino", "idiotas", "safado", "otario", "otário",
]

_PADRAO_PALAVRAO = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in PALAVRAS_IMPROPRIAS) + r")\w*\b",
    re.IGNORECASE,
)

_PADRAO_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_PADRAO_CARTAO = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_PADRAO_TELEFONE = re.compile(r"\b\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b")


def _mascarar_palavra(match: re.Match) -> str:
    palavra = match.group(0)
    if len(palavra) <= 2:
        return "*" * len(palavra)
    return palavra[0] + "*" * (len(palavra) - 2) + palavra[-1]


def ofuscar_palavroes(texto: str) -> str:
    return _PADRAO_PALAVRAO.sub(_mascarar_palavra, texto)


def mascarar_dados_pessoais(texto: str) -> str:
    texto = _PADRAO_CPF.sub("[CPF OCULTADO]", texto)
    texto = _PADRAO_TELEFONE.sub("[TELEFONE OCULTADO]", texto)
    texto = _PADRAO_CARTAO.sub("[NÚMERO OCULTADO]", texto)
    return texto


def higienizar(texto: str) -> str:
    return mascarar_dados_pessoais(ofuscar_palavroes(texto))
