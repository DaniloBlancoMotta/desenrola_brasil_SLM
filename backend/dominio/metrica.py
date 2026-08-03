"""Grandezas mensuraveis do conjunto de dados."""

from __future__ import annotations

from enum import Enum


def _milhar_br(valor: float, casas: int = 0) -> str:
    formatado = f"{valor:,.{casas}f}"
    return formatado.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


class Metrica(Enum):
    VOLUME = "volume"
    NUMERO_OPERACOES = "numero_operacoes"

    @property
    def coluna(self) -> str:
        return {
            Metrica.VOLUME: "VOLUME_OPERACOES",
            Metrica.NUMERO_OPERACOES: "NUMERO_OPERACOES",
        }[self]

    @property
    def rotulo(self) -> str:
        return {
            Metrica.VOLUME: "Volume renegociado (R$)",
            Metrica.NUMERO_OPERACOES: "Numero de operacoes",
        }[self]

    def formatar(self, valor: float) -> str:
        if self is Metrica.VOLUME:
            return f"R$ {_milhar_br(valor, 2)}"
        return f"{_milhar_br(valor)} operacoes"

    def formatar_compacto(self, valor: float) -> str:
        """Versao curta para rotular a marca: 'R$ 1,0 bi' cabe onde o valor cheio nao."""
        for limite, sufixo in ((1e9, "bi"), (1e6, "mi"), (1e3, "mil")):
            if abs(valor) >= limite:
                texto = f"{_milhar_br(valor / limite, 1)} {sufixo}"
                break
        else:
            texto = _milhar_br(valor)
        return f"R$ {texto}" if self is Metrica.VOLUME else texto
