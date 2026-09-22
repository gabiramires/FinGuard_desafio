"""Vocabulário controlado do domínio FinGuard."""

from enum import Enum


class Categoria(str, Enum):
    COBRANCA_INDEVIDA = "Cobrança Indevida"
    ATENDIMENTO = "Atendimento"
    FRAUDE_SEGURANCA = "Fraude/Segurança"
    PRODUTO_SERVICO = "Produto/Serviço"
    CANCELAMENTO = "Cancelamento"
    OUTROS = "Outros"


class Produto(str, Enum):
    CARTAO_CREDITO = "Cartão de Crédito"
    CONTA_CORRENTE = "Conta Corrente"
    EMPRESTIMO = "Empréstimo"
    INVESTIMENTOS = "Investimentos"
    SEGUROS = "Seguros"
    NAO_IDENTIFICADO = "Não Identificado"


class Sentimento(str, Enum):
    POSITIVO = "Positivo"
    NEUTRO = "Neutro"
    NEGATIVO = "Negativo"
    CRITICO = "Crítico"


class Urgencia(str, Enum):
    BAIXA = "Baixa"
    MEDIA = "Média"
    ALTA = "Alta"
    CRITICA = "Crítica"


class NivelRisco(str, Enum):
    BAIXO = "Baixo"
    MEDIO = "Médio"
    ALTO = "Alto"
    CRITICO = "Crítico"
