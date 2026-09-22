"""Carregamento e versionamento de prompts desacoplados dos agentes."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Type

import yaml
from pydantic import BaseModel

from src.domain.registry import resolver_output_model

RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
PACK_PADRAO = RAIZ_PROJETO / "assets" / "pack.yaml"


@dataclass(frozen=True)
class PromptAsset:
    version: str
    agent_id: str
    output_model_name: str
    output_model: Type[BaseModel]
    system_template: str
    user_template: str
    source_path: Path
    content_hash: str

    def render(self, **variaveis: Any) -> tuple[str, str]:
        valores = {chave: valor if valor is not None else "não informado" for chave, valor in variaveis.items()}
        return (
            self.system_template.format(**valores),
            self.user_template.format(**valores),
        )


@dataclass(frozen=True)
class DomainPack:
    version: str
    prompts: dict[str, PromptAsset]
    policy_path: Path
    gold_path: Path | None
    pack_hash: str


def _sha256_bytes(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def _sha256_arquivo(caminho: Path) -> str:
    return _sha256_bytes(caminho.read_bytes())


def carregar_prompt(caminho: Path) -> PromptAsset:
    conteudo = caminho.read_bytes()
    dados = json.loads(conteudo.decode("utf-8"))
    output_model = resolver_output_model(dados["output_model"])
    return PromptAsset(
        version=dados["version"],
        agent_id=dados["agent_id"],
        output_model_name=dados["output_model"],
        output_model=output_model,
        system_template=dados["system_template"],
        user_template=dados["user_template"],
        source_path=caminho,
        content_hash=_sha256_bytes(conteudo),
    )


def carregar_pack(caminho: Path | None = None) -> DomainPack:
    caminho_pack = caminho or PACK_PADRAO
    manifesto = yaml.safe_load(caminho_pack.read_text(encoding="utf-8"))
    raiz = caminho_pack.parent.parent if caminho_pack.parent.name == "assets" else caminho_pack.parent

    prompts: dict[str, PromptAsset] = {}
    hashes_prompts: list[str] = []
    for papel, relativo in manifesto["prompts"].items():
        caminho_prompt = raiz / relativo if not Path(relativo).is_absolute() else Path(relativo)
        prompt = carregar_prompt(caminho_prompt)
        prompts[papel] = prompt
        hashes_prompts.append(prompt.content_hash)

    policy_path = raiz / manifesto["policy"]
    gold_relativo = manifesto.get("gold")
    gold_path = raiz / gold_relativo if gold_relativo else None

    pack_hash = _sha256_bytes("|".join([manifesto["version"], *sorted(hashes_prompts), _sha256_arquivo(policy_path)]).encode())

    return DomainPack(
        version=manifesto["version"],
        prompts=prompts,
        policy_path=policy_path,
        gold_path=gold_path,
        pack_hash=pack_hash,
    )


def prompt_hash_conjunto(pack: DomainPack) -> str:
    partes = sorted(prompt.content_hash for prompt in pack.prompts.values())
    return _sha256_bytes("|".join(partes).encode())
