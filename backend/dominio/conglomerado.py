"""Conglomerado financeiro, com identidade estavel ao longo de todo o historico.

O Banco Central trocou o codigo e o nome dos conglomerados em jan/2025: "BB"
(cod. 49906) so aparece ate 202412 e "BB - PRUDENCIAL" (cod. 80329) comeca em
202501, sem sobreposicao. Tratados como entidades distintas, qualquer serie
temporal cairia a zero em 2025 e os rankings dividiriam cada instituicao em
duas. Por isso a identidade vem do nome canonizado, nunca do codigo.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

SUFIXO_PRUDENCIAL = " - PRUDENCIAL"


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


@dataclass(frozen=True)
class Conglomerado:
    """Identidade e o nome canonico; a exibicao preserva a acentuacao original."""

    nome_canonico: str
    nome_exibicao: str = field(compare=False, default="")

    def __post_init__(self) -> None:
        if not self.nome_canonico:
            raise ValueError("Conglomerado sem nome")
        if not self.nome_exibicao:
            object.__setattr__(self, "nome_exibicao", self.nome_canonico)

    @classmethod
    def de_bruto(cls, nome: str) -> Conglomerado:
        """Constroi a partir do valor cru do CSV, unificando a quebra de jan/2025."""
        exibicao = nome.strip().upper()
        if exibicao.endswith(SUFIXO_PRUDENCIAL):
            exibicao = exibicao[: -len(SUFIXO_PRUDENCIAL)].strip()
        return cls(nome_canonico=_sem_acento(exibicao), nome_exibicao=exibicao)

    def __str__(self) -> str:
        return self.nome_exibicao
