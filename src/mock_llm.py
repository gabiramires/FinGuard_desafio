"""Provider 'mock': heurísticas por palavra-chave, sem chamar LLM nenhum.

Existe para permitir rodar o pipeline (nível 1 e nível 2) de ponta a ponta
sem custo e sem chave de API — útil em desenvolvimento/testes e como
demonstração offline. NÃO deve ser usado para a avaliação final (a
qualidade da classificação real depende do LLM real via provider
'anthropic' ou 'bedrock', configurado em FINGUARD_LLM_PROVIDER).
"""

import re
import unicodedata

from . import schemas


def _normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def _contem_algum(texto_normalizado: str, termos: list[str]) -> bool:
    return any(termo in texto_normalizado for termo in termos)


_TERMOS_FRAUDE = [
    "fraude", "nao fiz", "nao reconheco", "clonad", "hackea", "invadi",
    "golpe", "roubaram", "uso indevido", "acesso indevido", "nao autorizei",
]
_TERMOS_COBRANCA = [
    "cobranca indevida", "cobrado duas vezes", "cobranca duplicada",
    "tarifa indevida", "taxa indevida", "cobraram", "estorno", "duplicidade",
]
_TERMOS_ATENDIMENTO = [
    "ninguem resolve", "nao resolve", "mal atendid", "atendimento pessimo",
    "descaso", "ninguem me atende", "sem retorno",
]
_TERMOS_CANCELAMENTO = ["cancelar", "cancelamento", "encerrar a conta", "encerramento"]
_TERMOS_PRODUTO_SERVICO = ["defeito", "nao funciona", "erro no aplicativo", "app trava", "fora do ar"]

_TERMOS_PRODUTO = {
    schemas.Produto.CARTAO_CREDITO: ["cartao de credito", "cartao", "fatura", "anuidade"],
    schemas.Produto.CONTA_CORRENTE: ["conta corrente", "conta", "extrato", "pix", "tarifa"],
    schemas.Produto.EMPRESTIMO: ["emprestimo", "parcela", "financiamento"],
    schemas.Produto.INVESTIMENTOS: ["investimento", "aplicacao financeira", "resgate", "rentabilidade", "fundo"],
    schemas.Produto.SEGUROS: ["seguro", "sinistro", "apolice", "premio do seguro"],
}

_TERMOS_NEGATIVOS = ["pessimo", "horrivel", "absurdo", "ridiculo", "revoltad", "furios", "insuportavel"]
_TERMOS_POSITIVOS = ["obrigado", "gratidao", "excelente", "otimo atendimento", "resolvido rapido", "parabens"]
_TERMOS_ESCALACAO = ["banco central", "procon", "justica", "juizado", "processo judicial"]
_TERMOS_MULTIPLAS_TENTATIVAS = ["terceira vez", "varias vezes", "diversas vezes", "nunca resolve", "de novo"]

_TERMOS_LGPD = ["lgpd", "dados pessoais", "sigilo bancario", "vazamento de dados"]
_TERMOS_REPUTACIONAL = ["redes sociais", "imprensa", "reclame aqui", "twitter", "instagram", "viralizou", "viral"]


def _extrair_produto_informado(user: str) -> schemas.Produto | None:
    match = re.search(r"produto informado:\s*(.+)", user, re.IGNORECASE)
    if not match:
        return None
    valor = _normalizar(match.group(1).strip())
    if not valor or "nao informado" in valor:
        return None
    for produto in schemas.Produto:
        if _normalizar(produto.value) in valor or valor in _normalizar(produto.value):
            return produto
    return None


def _extrair_canal(user: str) -> str:
    match = re.search(r"canal:\s*(.+)", user, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _inferir_produto(texto_normalizado: str) -> schemas.Produto:
    for produto, termos in _TERMOS_PRODUTO.items():
        if _contem_algum(texto_normalizado, termos):
            return produto
    return schemas.Produto.NAO_IDENTIFICADO


def _inferir_categoria(texto_normalizado: str) -> schemas.Categoria:
    if _contem_algum(texto_normalizado, _TERMOS_FRAUDE):
        return schemas.Categoria.FRAUDE_SEGURANCA
    if _contem_algum(texto_normalizado, _TERMOS_COBRANCA):
        return schemas.Categoria.COBRANCA_INDEVIDA
    if _contem_algum(texto_normalizado, _TERMOS_CANCELAMENTO):
        return schemas.Categoria.CANCELAMENTO
    if _contem_algum(texto_normalizado, _TERMOS_ATENDIMENTO):
        return schemas.Categoria.ATENDIMENTO
    if _contem_algum(texto_normalizado, _TERMOS_PRODUTO_SERVICO):
        return schemas.Categoria.PRODUTO_SERVICO
    return schemas.Categoria.OUTROS


def _inferir_sentimento(texto_normalizado: str, canal_critico: bool, fraude: bool) -> schemas.Sentimento:
    if fraude or canal_critico:
        return schemas.Sentimento.CRITICO
    if _contem_algum(texto_normalizado, _TERMOS_NEGATIVOS):
        return schemas.Sentimento.NEGATIVO
    if _contem_algum(texto_normalizado, _TERMOS_POSITIVOS):
        return schemas.Sentimento.POSITIVO
    return schemas.Sentimento.NEUTRO


def _inferir_urgencia(texto_normalizado: str, canal_critico: bool, fraude: bool) -> schemas.Urgencia:
    if canal_critico or fraude or _contem_algum(texto_normalizado, _TERMOS_ESCALACAO):
        return schemas.Urgencia.CRITICA
    if _contem_algum(texto_normalizado, _TERMOS_MULTIPLAS_TENTATIVAS):
        return schemas.Urgencia.ALTA
    if _contem_algum(texto_normalizado, _TERMOS_NEGATIVOS + _TERMOS_COBRANCA):
        return schemas.Urgencia.MEDIA
    return schemas.Urgencia.BAIXA


def _extrair_texto_reclamacao(user: str) -> str:
    match = re.search(r"texto da reclama[cç][aã]o:\s*(.+)", user, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else user.strip()


def _analisar(user: str) -> schemas.AnaliseEstruturada:
    texto_original = _extrair_texto_reclamacao(user)
    texto_normalizado = _normalizar(user)
    canal = _extrair_canal(user)
    canal_critico = _normalizar(canal) in {"banco central", "procon"}
    fraude = _contem_algum(texto_normalizado, _TERMOS_FRAUDE)

    categoria = _inferir_categoria(texto_normalizado)
    produto = _extrair_produto_informado(user) or _inferir_produto(texto_normalizado)
    sentimento = _inferir_sentimento(texto_normalizado, canal_critico, fraude)
    urgencia = _inferir_urgencia(texto_normalizado, canal_critico, fraude)

    trecho = texto_original[:180].strip()
    resumo = f"Cliente relata caso classificado como {categoria.value} envolvendo {produto.value}. Trecho original: \"{trecho}\""

    return schemas.AnaliseEstruturada(
        categoria=categoria,
        produto=produto,
        sentimento=sentimento,
        urgencia=urgencia,
        resumo=resumo,
    )


def _avaliar_risco(user: str) -> schemas.ParecerRisco:
    texto_normalizado = _normalizar(user)

    indicios_fraude = _contem_algum(texto_normalizado, _TERMOS_FRAUDE)
    indicios_lgpd = _contem_algum(texto_normalizado, _TERMOS_LGPD)
    risco_reputacional = _contem_algum(texto_normalizado, _TERMOS_REPUTACIONAL)
    escalacao_mencionada = _contem_algum(texto_normalizado, _TERMOS_ESCALACAO)

    if indicios_fraude or escalacao_mencionada or "urgencia: critica" in texto_normalizado:
        nivel = schemas.NivelRisco.CRITICO
    elif indicios_lgpd or risco_reputacional or "urgencia: alta" in texto_normalizado:
        nivel = schemas.NivelRisco.ALTO
    elif "urgencia: media" in texto_normalizado:
        nivel = schemas.NivelRisco.MEDIO
    else:
        nivel = schemas.NivelRisco.BAIXO

    motivos = []
    if indicios_fraude:
        motivos.append("indícios de fraude/transação não autorizada")
    if indicios_lgpd:
        motivos.append("possível violação regulatória (LGPD/sigilo bancário)")
    if risco_reputacional:
        motivos.append("menção a canal com risco reputacional")
    if escalacao_mencionada:
        motivos.append("menção a Banco Central/Procon/Justiça")
    if not motivos:
        motivos.append("nenhum indício relevante identificado no texto")

    justificativa = f"Nível '{nivel.value}' atribuído por: " + "; ".join(motivos) + "."

    return schemas.ParecerRisco(
        nivel_risco=nivel,
        justificativa=justificativa,
        indicios_fraude=indicios_fraude,
        indicios_violacao_regulatoria=indicios_lgpd,
        risco_reputacional=risco_reputacional,
        necessita_escalacao_imediata=nivel in (schemas.NivelRisco.ALTO, schemas.NivelRisco.CRITICO),
    )


def gerar(system: str, user: str, schema):
    if schema is schemas.AnaliseEstruturada:
        return _analisar(user)
    if schema is schemas.ParecerRisco:
        return _avaliar_risco(user)
    raise NotImplementedError(f"mock_llm não sabe gerar o schema {schema!r}")
