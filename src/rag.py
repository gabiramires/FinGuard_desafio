"""Compatibilidade — API funcional sobre PoliticaRAG."""

from src.infrastructure.rag.politica import PoliticaRAG

_rag = PoliticaRAG()


def buscar_contexto(consulta: str, k: int = 3) -> str:
    return _rag.buscar_contexto(consulta, k)


def regra_canal_critico(canal: str) -> bool:
    return PoliticaRAG.regra_canal_critico(canal)


def contexto_secao_canal(canal: str) -> str:
    return _rag.contexto_secao_canal(canal)


def contexto_secao_produto(produto: str) -> str:
    return _rag.buscar_contexto(f"procedimentos produto {produto}", k=1)


def contexto_secao_urgencia(urgencia: str) -> str:
    return _rag.buscar_contexto(f"classificacao urgencia acoes imediatas {urgencia}", k=1)
