"""Politica de visualizacao: decide se ha grafico e de que forma.

Regra deterministica, testavel sem LLM. O dominio descreve o grafico, mas nao
conhece Plotly -- traduzir a especificacao em figura e trabalho da
infraestrutura.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dominio.consulta import ResultadoConsulta, Serie
from dominio.dimensao import Dimensao
from dominio.metrica import Metrica

LIMITE_CATEGORIAS = 15
"""Uma barra com 64 conglomerados nao comunica nada."""

LIMITE_SERIES = 8
"""Teto da paleta categorica. A nona serie nao ganha cor nova: e agrupada fora."""

CATEGORIAS_PARA_VERTICAL = 6
"""Abaixo disso a barra vertical fica larga demais; na horizontal a altura controla."""


class TipoGrafico(Enum):
    BARRA_VERTICAL = "barra_vertical"
    BARRA_HORIZONTAL = "barra_horizontal"
    LINHA = "linha"


@dataclass(frozen=True)
class EspecificacaoGrafico:
    tipo: TipoGrafico
    titulo: str
    rotulo_categoria: str
    rotulo_valor: str
    series: tuple[Serie, ...]
    metrica: Metrica = Metrica.VOLUME
    """Necessaria para rotular as marcas na forma compacta."""

    cor_por_categoria: bool = False
    """Cada barra do ranking recebe um slot proprio, em vez de todas na mesma cor."""

    @property
    def linhas(self):
        return self.series[0].linhas if self.series else ()

    @property
    def comparativo(self) -> bool:
        return len(self.series) > 1

    @property
    def categorias_exibidas(self) -> int:
        return max((len(serie.linhas) for serie in self.series), default=0)

    @property
    def series_exibidas(self) -> int:
        return len(self.series)


class PoliticaVisualizacao:
    def decidir(self, resultado: ResultadoConsulta) -> EspecificacaoGrafico | None:
        if resultado.vazio:
            return None
        # Um unico ponto e uma resposta em numero; duas series de um ponto cada
        # ja e uma comparacao que vale desenhar.
        if not resultado.comparativo and resultado.maior_serie < 2:
            return None

        tipo = self._tipo_para(resultado)
        # Num ranking a cor identifica a categoria; numa serie temporal ou numa
        # comparacao ela ja identifica a serie e nao pode ser reaproveitada.
        cor_por_categoria = not resultado.comparativo and tipo is not TipoGrafico.LINHA

        return EspecificacaoGrafico(
            tipo=tipo,
            titulo=self._titulo(resultado),
            rotulo_categoria=resultado.dimensao.rotulo,
            rotulo_valor=resultado.metrica.rotulo,
            series=self._truncar(resultado, LIMITE_CATEGORIAS),
            metrica=resultado.metrica,
            cor_por_categoria=cor_por_categoria,
        )

    @staticmethod
    def _truncar(resultado: ResultadoConsulta, limite_categorias: int) -> tuple[Serie, ...]:
        # A paleta tem ordem fixa e nao cicla: series alem do teto repetiriam
        # cores e destruiriam a identidade visual.
        resultado = (
            resultado
            if len(resultado.series) <= LIMITE_SERIES
            else ResultadoConsulta(
                series=resultado.series[:LIMITE_SERIES],
                dimensao=resultado.dimensao,
                metrica=resultado.metrica,
                descricao_filtros=resultado.descricao_filtros,
                total_de_grupos=resultado.total_de_grupos,
            )
        )

        if not resultado.dimensao.ordena_por_valor:
            return resultado.series  # serie temporal: cortar esconderia a tendencia

        if not resultado.comparativo:
            return (Serie(resultado.linhas[:limite_categorias], resultado.series[0].nome),)

        # Comparativo por categoria: as series precisam dos MESMOS rotulos, ou
        # as barras agrupadas ficariam desalinhadas. O corte usa a soma entre
        # series para escolher quais categorias sobrevivem.
        soma_por_rotulo: dict[str, float] = {}
        for serie in resultado.series:
            for linha in serie.linhas:
                soma_por_rotulo[linha.rotulo] = soma_por_rotulo.get(linha.rotulo, 0.0) + linha.valor
        mantidos = {
            rotulo
            for rotulo, _ in sorted(soma_por_rotulo.items(), key=lambda par: -par[1])[
                :limite_categorias
            ]
        }
        return tuple(
            Serie(tuple(linha for linha in serie.linhas if linha.rotulo in mantidos), serie.nome)
            for serie in resultado.series
        )

    @staticmethod
    def _tipo_para(resultado: ResultadoConsulta) -> TipoGrafico:
        if resultado.dimensao is Dimensao.PERIODO:
            return TipoGrafico.LINHA
        if resultado.comparativo:
            # Barras agrupadas na horizontal confundem mais do que ajudam.
            return TipoGrafico.BARRA_VERTICAL
        if resultado.dimensao in (Dimensao.CONGLOMERADO, Dimensao.TIPO):
            # Nomes longos ("BCO DO NORDESTE DO BRASIL S.A.", "Faixa 1 (pessoas
            # fisicas)") ficam ilegiveis rotacionados no eixo x.
            return TipoGrafico.BARRA_HORIZONTAL
        if resultado.maior_serie < CATEGORIAS_PARA_VERTICAL:
            # Poucas colunas verticais viram blocos largos; na horizontal a
            # altura do grafico controla a espessura da marca.
            return TipoGrafico.BARRA_HORIZONTAL
        return TipoGrafico.BARRA_VERTICAL

    @staticmethod
    def _titulo(resultado: ResultadoConsulta) -> str:
        base = f"{resultado.metrica.rotulo} por {resultado.dimensao.rotulo.lower()}"
        if resultado.descricao_filtros:
            return f"{base} - {resultado.descricao_filtros}"
        return base
