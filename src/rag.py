"""RAG simples sobre a Política Interna (POL-SAC-001).

O documento é único e curto, então não há necessidade de um vector store
externo: o texto é dividido em chunks por seção (níveis ## e ###) e a
recuperação é feita por sobreposição de palavras-chave. Isso é suficiente
para dar ao LLM o trecho certo da política (prazo, procedimento por
produto/canal) sem a complexidade/custo de embeddings + índice vetorial.
"""

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CAMINHO_POLITICA = Path(__file__).resolve().parent.parent / "ks_politica_interna.md"

CANAIS_URGENCIA_AUTOMATICA_CRITICA = {"banco central", "procon"}


@dataclass(frozen=True)
class Chunk:
    titulo: str
    texto: str


def _normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def carregar_chunks() -> tuple[Chunk, ...]:
    conteudo = CAMINHO_POLITICA.read_text(encoding="utf-8")
    blocos = re.split(r"\n(?=#{2,3} )", conteudo)
    chunks = []
    for bloco in blocos:
        bloco = bloco.strip()
        if not bloco:
            continue
        primeira_linha = bloco.splitlines()[0]
        titulo = primeira_linha.lstrip("#").strip()
        chunks.append(Chunk(titulo=titulo, texto=bloco))
    return tuple(chunks)


def buscar_contexto(consulta: str, k: int = 3) -> str:
    """Retorna os k chunks da política com maior sobreposição de termos com a consulta."""
    termos_consulta = set(_normalizar(consulta).split())
    pontuados = []
    for chunk in carregar_chunks():
        termos_chunk = set(_normalizar(chunk.texto).split())
        pontuacao = len(termos_consulta & termos_chunk)
        if pontuacao > 0:
            pontuados.append((pontuacao, chunk))
    pontuados.sort(key=lambda item: item[0], reverse=True)
    selecionados = [chunk for _, chunk in pontuados[:k]]
    if not selecionados:
        return ""
    return "\n\n---\n\n".join(chunk.texto for chunk in selecionados)


def regra_canal_critico(canal: str) -> bool:
    """Seção 4.3 da política: Banco Central/Procon = urgência automaticamente crítica."""
    return _normalizar(canal or "") in CANAIS_URGENCIA_AUTOMATICA_CRITICA


def contexto_secao_canal(canal: str) -> str:
    return buscar_contexto(f"procedimentos canal origem {canal}", k=1)


def contexto_secao_produto(produto: str) -> str:
    return buscar_contexto(f"procedimentos produto {produto}", k=1)


def contexto_secao_urgencia(urgencia: str) -> str:
    return buscar_contexto(f"classificacao urgencia acoes imediatas {urgencia}", k=1)
