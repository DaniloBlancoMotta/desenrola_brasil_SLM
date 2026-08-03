"""Unidade da federacao, validada contra as 27 siglas oficiais."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

NOMES_POR_SIGLA = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AM": "Amazonas",
    "AP": "Amapa",
    "BA": "Bahia",
    "CE": "Ceara",
    "DF": "Distrito Federal",
    "ES": "Espirito Santo",
    "GO": "Goias",
    "MA": "Maranhao",
    "MG": "Minas Gerais",
    "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso",
    "PA": "Para",
    "PB": "Paraiba",
    "PE": "Pernambuco",
    "PI": "Piaui",
    "PR": "Parana",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RO": "Rondonia",
    "RR": "Roraima",
    "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina",
    "SE": "Sergipe",
    "SP": "Sao Paulo",
    "TO": "Tocantins",
}

_SIGLAS_POR_NOME = {
    unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().upper(): sigla
    for sigla, nome in NOMES_POR_SIGLA.items()
}


@dataclass(frozen=True)
class UnidadeFederacao:
    sigla: str

    def __post_init__(self) -> None:
        if self.sigla not in NOMES_POR_SIGLA:
            raise ValueError(f"UF desconhecida: {self.sigla!r}")

    @classmethod
    def de_texto(cls, valor: str) -> UnidadeFederacao:
        """Aceita a sigla ou o nome por extenso, com ou sem acento."""
        bruto = valor.strip()
        sem_acento = (
            unicodedata.normalize("NFKD", bruto).encode("ascii", "ignore").decode().upper()
        )
        if sem_acento in _SIGLAS_POR_NOME:
            return cls(_SIGLAS_POR_NOME[sem_acento])
        return cls(sem_acento)

    @property
    def nome(self) -> str:
        return NOMES_POR_SIGLA[self.sigla]

    def __str__(self) -> str:
        return self.sigla
