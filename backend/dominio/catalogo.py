"""Vocabulario valido do conjunto de dados, extraido do CSV na subida.

Alimenta o system prompt para que o LLM traduza "Banco do Brasil" em "BB" e
saiba o intervalo de datas disponivel antes de chamar a ferramenta.
"""

from __future__ import annotations

from dataclasses import dataclass

from dominio.periodo import Periodo


FONTE = "Desenrola Brasil — Banco Central do Brasil"
URL_FONTE = "https://www.bcb.gov.br/pda/desig/desenrola/dados_desenrola.csv"


@dataclass(frozen=True)
class ResumoDaBase:
    """O que a interface mostra sobre a origem dos numeros que exibe."""

    periodo_inicio: Periodo
    periodo_fim: Periodo
    meses: int
    registros: int
    conglomerados: int
    ufs: int
    modalidades: tuple[str, ...]
    volume_total: float
    operacoes_totais: int
    fonte: str = FONTE
    url: str = URL_FONTE

    @property
    def periodo(self) -> str:
        return f"{self.periodo_inicio} a {self.periodo_fim}"


@dataclass(frozen=True)
class Catalogo:
    conglomerados: tuple[str, ...]
    ufs: tuple[str, ...]
    periodo_inicio: Periodo
    periodo_fim: Periodo

    def resumo_textual(self, limite_conglomerados: int = 45) -> str:
        principais = self.conglomerados[:limite_conglomerados]
        restantes = len(self.conglomerados) - len(principais)
        sufixo = f" (e mais {restantes} de menor porte)" if restantes > 0 else ""
        return (
            f"Periodo disponivel: {self.periodo_inicio} a {self.periodo_fim}.\n"
            f"UFs: {', '.join(self.ufs)}.\n"
            f"Conglomerados{sufixo}: {'; '.join(principais)}."
        )
