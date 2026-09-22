"""Modelos de saída dos agentes — contratos do domínio."""

from pydantic import BaseModel, Field

from .enums import Categoria, NivelRisco, Produto, Sentimento, Urgencia


class AnaliseEstruturada(BaseModel):
    """Saída do agente de estruturação (Nível 1)."""

    categoria: Categoria
    produto: Produto
    sentimento: Sentimento
    urgencia: Urgencia
    resumo: str = Field(
        description="Resumo de 2-3 linhas em linguagem padronizada, sem palavras impróprias ou dados pessoais."
    )


class ParecerRisco(BaseModel):
    """Saída do agente de risco e conformidade (Nível 2)."""

    nivel_risco: NivelRisco
    justificativa: str = Field(
        description="Justificativa objetiva, citando o indício e a regra da política interna aplicável."
    )
    indicios_fraude: bool = False
    indicios_violacao_regulatoria: bool = False
    risco_reputacional: bool = False
    necessita_escalacao_imediata: bool = False


class RegistroReclamacao(BaseModel):
    """Registro consolidado por reclamação."""

    id: str
    canal: str
    data_reclamacao: str | None = None
    texto_reclamacao: str
    analise: AnaliseEstruturada
    parecer_risco: ParecerRisco | None = None
