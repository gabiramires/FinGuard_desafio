"""Modelos de dados trocados entre os agentes do FinGuard."""

from enum import Enum

from pydantic import BaseModel, Field


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


class AnaliseEstruturada(BaseModel):
    """Saída do Agente 1 — Recepção e Estruturação (Nível 1 do desafio)."""

    categoria: Categoria
    produto: Produto
    sentimento: Sentimento
    urgencia: Urgencia
    resumo: str = Field(
        description="Resumo de 2-3 linhas em linguagem padronizada, sem palavras impróprias ou dados pessoais."
    )


class ParecerRisco(BaseModel):
    """Saída do Agente 2 — Análise de Risco e Conformidade (Nível 2)."""

    nivel_risco: NivelRisco
    justificativa: str = Field(description="Justificativa objetiva, citando o indício e a regra da política interna aplicável.")
    indicios_fraude: bool = False
    indicios_violacao_regulatoria: bool = False
    risco_reputacional: bool = False
    necessita_escalacao_imediata: bool = False


class RegistroReclamacao(BaseModel):
    """Registro final consolidado pelo Agente 3 para uma reclamação."""

    id: str
    canal: str
    data_reclamacao: str | None = None
    texto_reclamacao: str
    analise: AnaliseEstruturada
    parecer_risco: ParecerRisco | None = None
