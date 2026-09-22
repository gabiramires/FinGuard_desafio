"""RAG por palavra-chave sobre a política interna."""

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CAMINHO_POLITICA_PADRAO = Path(__file__).resolve().parent.parent.parent.parent / "ks_politica_interna.md"
CANAIS_URGENCIA_AUTOMATICA_CRITICA = {"banco central", "procon"}


@dataclass(frozen=True)
class Chunk:
    titulo: str
    texto: str


def _normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


@lru_cache(maxsize=4)
def _carregar_chunks_caminho(caminho: str) -> tuple[Chunk, ...]:
    conteudo = Path(caminho).read_text(encoding="utf-8")
    blocos = re.split(r"\n(?=#{2,3} )", conteudo)
    chunks: list[Chunk] = []
    for bloco in blocos:
        bloco = bloco.strip()
        if not bloco:
            continue
        titulo = bloco.splitlines()[0].lstrip("#").strip()
        chunks.append(Chunk(titulo=titulo, texto=bloco))
    return tuple(chunks)


class PoliticaRAG:
    def __init__(self, caminho_politica: Path | None = None):
        self.caminho = caminho_politica or CAMINHO_POLITICA_PADRAO

    def carregar_chunks(self) -> tuple[Chunk, ...]:
        return _carregar_chunks_caminho(str(self.caminho.resolve()))

    def buscar_contexto(self, consulta: str, k: int = 3) -> str:
        termos_consulta = set(_normalizar(consulta).split())
        pontuados: list[tuple[int, Chunk]] = []
        for chunk in self.carregar_chunks():
            termos_chunk = set(_normalizar(chunk.texto).split())
            pontuacao = len(termos_consulta & termos_chunk)
            if pontuacao > 0:
                pontuados.append((pontuacao, chunk))
        pontuados.sort(key=lambda item: item[0], reverse=True)
        selecionados = [chunk for _, chunk in pontuados[:k]]
        if not selecionados:
            return ""
        return "\n\n---\n\n".join(chunk.texto for chunk in selecionados)

    @staticmethod
    def regra_canal_critico(canal: str) -> bool:
        return _normalizar(canal or "") in CANAIS_URGENCIA_AUTOMATICA_CRITICA

    def contexto_secao_canal(self, canal: str) -> str:
        return self.buscar_contexto(f"procedimentos canal origem {canal}", k=1)
