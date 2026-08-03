"""Eixos pelos quais os dados podem ser agrupados."""

from __future__ import annotations

from enum import Enum


class Dimensao(Enum):
    CONGLOMERADO = "conglomerado"
    UF = "uf"
    PERIODO = "periodo"
    TIPO = "tipo"

    @property
    def rotulo(self) -> str:
        return {
            Dimensao.CONGLOMERADO: "Conglomerado financeiro",
            Dimensao.UF: "Unidade da federacao",
            Dimensao.PERIODO: "Mes",
            Dimensao.TIPO: "Modalidade",
        }[self]

    @property
    def ordena_por_valor(self) -> bool:
        """Periodo tem ordem natural cronologica; as demais rankeiam por valor."""
        return self is not Dimensao.PERIODO
