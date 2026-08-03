"""Modalidades do programa Desenrola.

Tipos 1 e 2 correspondem as faixas 1 e 2 do Desenrola pessoas fisicas
(Lei 14.690/2023); o tipo 3 e o Desenrola Pequenos Negocios (MP 1.213/2024).
"""

from __future__ import annotations

from enum import Enum


class TipoDesenrola(Enum):
    FAIXA_1 = 1
    FAIXA_2 = 2
    PEQUENOS_NEGOCIOS = 3

    @classmethod
    def de_codigo(cls, codigo: int) -> TipoDesenrola:
        return cls(int(codigo))

    @property
    def descricao(self) -> str:
        return {
            TipoDesenrola.FAIXA_1: "Faixa 1 (pessoas fisicas)",
            TipoDesenrola.FAIXA_2: "Faixa 2 (pessoas fisicas)",
            TipoDesenrola.PEQUENOS_NEGOCIOS: "Pequenos Negocios",
        }[self]

    def __str__(self) -> str:
        return self.descricao
