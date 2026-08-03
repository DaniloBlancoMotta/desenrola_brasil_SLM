"""Adaptador de visualizacao: traduz a especificacao do dominio em figura Plotly.

Aplica as especificacoes de marca do metodo de dataviz -- marcas finas, chrome
recessivo, espacadores na cor da superficie, texto em tokens de tinta e nunca na
cor da serie. As cores vivem em `paleta.py`, onde estao os resultados da
validacao.

Trocar de biblioteca de graficos significa reescrever apenas este arquivo.
"""

from __future__ import annotations

import json
from typing import Any

import plotly.graph_objects as go

from dominio.consulta import Serie
from dominio.visualizacao import EspecificacaoGrafico, TipoGrafico
from infraestrutura import paleta


class RenderizadorPlotly:
    def renderizar(self, especificacao: EspecificacaoGrafico) -> dict[str, Any]:
        figura = go.Figure(
            data=[
                self._traco(especificacao, serie, indice)
                for indice, serie in enumerate(especificacao.series)
            ],
            layout=self._layout(especificacao),
        )
        return json.loads(figura.to_json())

    def _traco(
        self, especificacao: EspecificacaoGrafico, serie: Serie, indice: int
    ) -> go.Scatter | go.Bar:
        rotulos = [linha.rotulo for linha in serie.linhas]
        valores = [linha.valor for linha in serie.linhas]
        cor = paleta.cor_da_serie(indice)
        nome = serie.nome or especificacao.rotulo_valor
        hover = self._hover(especificacao, nome)

        if especificacao.tipo is TipoGrafico.LINHA:
            return go.Scatter(
                x=rotulos,
                y=valores,
                name=nome,
                mode="lines+markers+text",
                line={"color": cor, "width": paleta.ESPESSURA_LINHA, "shape": "linear"},
                marker={
                    "size": paleta.TAMANHO_MARCADOR,
                    "color": cor,
                    # Anel na cor do fundo: os marcadores continuam legiveis
                    # onde as series se cruzam.
                    "line": {"width": paleta.ANEL_SUPERFICIE, "color": paleta.SUPERFICIE},
                },
                # Um numero em cada ponto seria ilegivel; so o fim da linha e rotulado.
                text=self._rotulo_final(especificacao, valores),
                textposition="middle right",
                textfont={"color": paleta.INK_SECUNDARIO, "size": 11},
                cliponaxis=False,
                hovertemplate=hover,
            )

        # Num ranking cada barra leva a cor da sua instituicao; numa comparacao
        # a cor pertence a serie inteira.
        cores = (
            paleta.cores_das_categorias(rotulos)
            if especificacao.cor_por_categoria
            else cor
        )
        largura = self._largura_da_marca(especificacao)
        # Valor na ponta da marca: sem ele o leitor depende do hover para saber
        # quanto vale cada barra. Em tinta neutra, nunca na cor do dado.
        textos = [especificacao.metrica.formatar_compacto(valor) for valor in valores]
        texto = {
            "textposition": "outside",
            "textfont": {"color": paleta.INK_SECUNDARIO, "size": 11},
            "cliponaxis": False,
        }

        def marcador(ordem_das_cores: list[str] | str) -> dict[str, Any]:
            return {
                "color": ordem_das_cores,
                "cornerradius": paleta.RAIO_CANTO,
                "line": {"width": 0},  # a separacao e o vao, nunca um contorno
            }

        if especificacao.tipo is TipoGrafico.BARRA_HORIZONTAL:
            # Plotly desenha o eixo y de baixo para cima; invertendo, o maior
            # valor aparece no topo, como se le um ranking. As cores precisam
            # inverter junto, senao a cor deixa de acompanhar a categoria.
            return go.Bar(
                x=valores[::-1],
                y=rotulos[::-1],
                name=nome,
                orientation="h",
                width=largura,
                marker=marcador(cores[::-1] if isinstance(cores, list) else cores),
                text=textos[::-1],
                hovertemplate=hover,
                **texto,
            )

        return go.Bar(
            x=rotulos,
            y=valores,
            name=nome,
            width=largura,
            marker=marcador(cores),
            text=textos,
            hovertemplate=hover,
            **texto,
        )

    @staticmethod
    def _rotulo_final(especificacao: EspecificacaoGrafico, valores: list[float]) -> list[str]:
        """Rotula so o ultimo ponto da linha -- e onde a serie termina a historia."""
        if not valores:
            return []
        return [""] * (len(valores) - 1) + [
            especificacao.metrica.formatar_compacto(valores[-1])
        ]

    @staticmethod
    def _largura_da_marca(especificacao: EspecificacaoGrafico) -> float:
        """A barra e capada em 24px; a banda restante fica de ar, de proposito."""
        if especificacao.tipo is TipoGrafico.BARRA_HORIZONTAL:
            extensao = RenderizadorPlotly._altura(especificacao) - paleta.CHROME_VERTICAL
        else:
            extensao = paleta.LARGURA_PLOT_TIPICA
        return paleta.largura_da_marca(
            extensao, especificacao.categorias_exibidas, especificacao.series_exibidas
        )

    @staticmethod
    def _hover(especificacao: EspecificacaoGrafico, nome: str) -> str:
        horizontal = especificacao.tipo is TipoGrafico.BARRA_HORIZONTAL
        metrica = especificacao.metrica
        eixo_categoria = "%{y}" if horizontal else "%{x}"
        eixo = "x" if horizontal else "y"
        # O separador vem de `separators` no layout; aqui so se define quantas
        # casas o numero tem.
        valor = f"%{{{eixo}:,.{metrica.casas_decimais}f}}"
        serie = f"<extra>{nome}</extra>" if especificacao.comparativo else "<extra></extra>"
        return (
            f"<b>{eixo_categoria}</b><br>"
            f"{metrica.prefixo}{valor}{metrica.sufixo}{serie}"
        )

    def _layout(self, especificacao: EspecificacaoGrafico) -> go.Layout:
        horizontal = especificacao.tipo is TipoGrafico.BARRA_HORIZONTAL
        eixo_valor = self._eixo_valor(especificacao)
        eixo_categoria = self._eixo_categoria()

        return go.Layout(
            title={
                "text": especificacao.titulo,
                "font": {"size": 14, "color": paleta.INK_SECUNDARIO},
                "x": 0,
                "xanchor": "left",
            },
            xaxis=eixo_valor if horizontal else eixo_categoria,
            yaxis=eixo_categoria if horizontal else eixo_valor,
            paper_bgcolor=paleta.SUPERFICIE,
            plot_bgcolor=paleta.SUPERFICIE,
            font={"color": paleta.INK_SECUNDARIO, "size": 12},
            # Padrao brasileiro: virgula decimal, ponto de milhar. Sem isto o
            # Plotly escreve "736,172.00", com os dois separadores trocados.
            separators=",.",
            barmode="group",
            # O vao entre marcas e feito de superficie, nao de contorno.
            bargap=0.3,
            bargroupgap=0.08,
            showlegend=especificacao.comparativo,
            legend={
                "orientation": "h",
                "y": -0.14,
                "x": 0,
                "font": {"color": paleta.INK_SECUNDARIO},
            },
            # Folga a direita para o rotulo na ponta da barra nao ser cortado.
            margin={"l": 8, "r": 72, "t": 44, "b": 8},
            height=self._altura(especificacao),
            autosize=True,
            hoverlabel={"bgcolor": paleta.SUPERFICIE, "bordercolor": paleta.EIXO},
        )

    @staticmethod
    def _eixo_valor(especificacao: EspecificacaoGrafico) -> dict[str, Any]:
        # Numa barra todo valor ja esta rotulado na ponta: a escala repetiria a
        # informacao. Numa linha so o ultimo ponto e rotulado, entao a grade
        # continua carregando os demais.
        rotulados = especificacao.tipo is not TipoGrafico.LINHA
        return {
            "title": {"text": "" if rotulados else especificacao.rotulo_valor,
                      "font": {"color": paleta.INK_MUTED}},
            "visible": not rotulados,
            "tickprefix": especificacao.metrica.prefixo,
            # Ticks arredondados: "R$ 2.500.000,00" polui a escala. O valor
            # exato, com centavos, aparece no hover e na tabela.
            "tickformat": ",.0f",
            # Hairline solida e recessiva: a grade nunca compete com o dado.
            "gridcolor": paleta.GRADE,
            "gridwidth": 1,
            "griddash": "solid",
            "zeroline": True,
            "zerolinecolor": paleta.EIXO,
            "zerolinewidth": 1,
            "showline": False,
            "tickfont": {"color": paleta.INK_MUTED},
            "separatethousands": True,
            # Sem isto a margem fixa corta os ticks longos ("2.500.000.000").
            "automargin": True,
        }

    @staticmethod
    def _eixo_categoria() -> dict[str, Any]:
        return {
            "title": {"text": ""},
            "showgrid": False,
            "showline": True,
            "linecolor": paleta.EIXO,
            "linewidth": 1,
            "tickfont": {"color": paleta.INK_MUTED},
            # "BCO DO NORDESTE DO BRASIL S.A." precisa de margem propria.
            "automargin": True,
        }

    @staticmethod
    def _altura(especificacao: EspecificacaoGrafico) -> int:
        if especificacao.tipo is TipoGrafico.BARRA_HORIZONTAL:
            # Altura proporcional as categorias: sem isso, tres barras ficariam
            # espremidas num grafico alto e quinze ficariam apertadas num baixo.
            return 120 + especificacao.categorias_exibidas * paleta.ALTURA_BANDA
        return 420
