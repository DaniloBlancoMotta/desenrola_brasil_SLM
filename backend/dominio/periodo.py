"""Mes de referencia dos dados, no formato AAAAMM usado pelo Banco Central."""

from __future__ import annotations

from dataclasses import dataclass

MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


@dataclass(frozen=True, order=True)
class Periodo:
    ano: int
    mes: int

    def __post_init__(self) -> None:
        if not 1 <= self.mes <= 12:
            raise ValueError(f"Mes fora do intervalo 1-12: {self.mes}")
        if not 2000 <= self.ano <= 2100:
            raise ValueError(f"Ano implausivel para o Desenrola: {self.ano}")

    @classmethod
    def de_aaaamm(cls, valor: int | str) -> Periodo:
        texto = str(valor).strip()
        if len(texto) != 6 or not texto.isdigit():
            raise ValueError(f"Periodo deve ter o formato AAAAMM, recebido: {valor!r}")
        return cls(ano=int(texto[:4]), mes=int(texto[4:]))

    @property
    def aaaamm(self) -> int:
        return self.ano * 100 + self.mes

    def __str__(self) -> str:
        return f"{MESES[self.mes - 1]}/{self.ano}"
