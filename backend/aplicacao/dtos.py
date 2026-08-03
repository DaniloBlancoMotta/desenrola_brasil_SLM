"""Objetos de transporte na fronteira HTTP. O dominio nunca cruza essa linha."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dominio.consulta import ResultadoConsulta


@dataclass(frozen=True)
class PerguntaDTO:
    pergunta: str


@dataclass(frozen=True)
class TabelaDTO:
    """Dados completos de uma consulta, prontos para o frontend tabular.

    Existe para que a tabela venha da fonte e nao da transcricao do modelo, que
    ve apenas um resumo truncado.
    """

    titulo: str
    dimensao: str
    metrica: str
    series: list[str]
    linhas: list[dict[str, Any]]
    """Formato largo: {"rotulo": "set/2023", "valores": {"SP": 103022.0}}."""

    @classmethod
    def de_resultado(cls, resultado: ResultadoConsulta) -> TabelaDTO:
        rotulos: list[str] = []
        for serie in resultado.series:
            for linha in serie.linhas:
                if linha.rotulo not in rotulos:
                    rotulos.append(linha.rotulo)

        nomes = [serie.nome or resultado.metrica.rotulo for serie in resultado.series]
        por_serie = [
            {linha.rotulo: linha.valor for linha in serie.linhas} for serie in resultado.series
        ]

        return cls(
            titulo=resultado.descricao_filtros,
            dimensao=resultado.dimensao.rotulo,
            metrica=resultado.metrica.rotulo,
            series=nomes,
            linhas=[
                {
                    "rotulo": rotulo,
                    "valores": {
                        nome: valores[rotulo]
                        for nome, valores in zip(nomes, por_serie)
                        if rotulo in valores
                    },
                }
                for rotulo in rotulos
            ],
        )


@dataclass(frozen=True)
class RespostaDTO:
    resposta: str
    graficos: list[dict[str, Any]] = field(default_factory=list)
    tabelas: list[TabelaDTO] = field(default_factory=list)

    @classmethod
    def de_agente(
        cls,
        texto: str,
        graficos: tuple[dict[str, Any], ...],
        resultados: tuple[ResultadoConsulta, ...],
    ) -> RespostaDTO:
        return cls(
            resposta=texto,
            graficos=list(graficos),
            tabelas=[
                TabelaDTO.de_resultado(resultado)
                for resultado in resultados
                if not resultado.vazio
            ],
        )
