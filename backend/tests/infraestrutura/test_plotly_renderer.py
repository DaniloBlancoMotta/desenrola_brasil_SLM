import json

import pytest

from dominio.consulta import LinhaResultado, Serie
from dominio.metrica import Metrica
from dominio.visualizacao import EspecificacaoGrafico, TipoGrafico
from infraestrutura import paleta
from infraestrutura.plotly_renderer import RenderizadorPlotly

LINHAS = (
    LinhaResultado("BRADESCO", 300.0),
    LinhaResultado("ITAU", 200.0),
    LinhaResultado("BB", 100.0),
)


def especificacao(tipo: TipoGrafico, series: tuple[Serie, ...] | None = None):
    series = series or (Serie(LINHAS),)
    return EspecificacaoGrafico(
        tipo=tipo,
        titulo="Volume por conglomerado",
        rotulo_categoria="Conglomerado",
        rotulo_valor="Volume (R$)",
        series=series,
        metrica=Metrica.VOLUME,
        # Mesma regra da politica: so o ranking de serie unica colore por barra,
        # e so ate o numero de slots da paleta.
        cor_por_categoria=(
            tipo is not TipoGrafico.LINHA
            and len(series) == 1
            and len(series[0].linhas) <= len(paleta.SERIES)
        ),
    )


@pytest.fixture
def renderizador() -> RenderizadorPlotly:
    return RenderizadorPlotly()


class TestRenderizadorPlotly:
    def test_serie_temporal_vira_scatter(self, renderizador):
        figura = renderizador.renderizar(especificacao(TipoGrafico.LINHA))
        assert figura["data"][0]["type"] == "scatter"

    def test_barra_vertical_usa_categorias_no_eixo_x(self, renderizador):
        traco = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))["data"][0]
        assert traco["type"] == "bar"
        assert list(traco["x"]) == ["BRADESCO", "ITAU", "BB"]

    def test_barra_horizontal_inverte_para_o_maior_ficar_no_topo(self, renderizador):
        """Plotly desenha o eixo y de baixo para cima."""
        traco = renderizador.renderizar(especificacao(TipoGrafico.BARRA_HORIZONTAL))["data"][0]
        assert traco["orientation"] == "h"
        assert list(traco["y"]) == ["BB", "ITAU", "BRADESCO"]

    def test_titulo_chega_ao_layout(self, renderizador):
        figura = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))
        assert figura["layout"]["title"]["text"] == "Volume por conglomerado"

    def test_serie_unica_nao_mostra_legenda(self, renderizador):
        figura = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))
        assert figura["layout"]["showlegend"] is False

    def test_saida_e_json_serializavel(self, renderizador):
        """A figura atravessa a fronteira HTTP; numpy nao pode vazar aqui."""
        figura = renderizador.renderizar(especificacao(TipoGrafico.LINHA))
        assert json.loads(json.dumps(figura)) == figura


class TestEspecificacoesDeMarca:
    def test_linha_tem_dois_pixels(self, renderizador):
        figura = renderizador.renderizar(especificacao(TipoGrafico.LINHA))
        assert figura["data"][0]["line"]["width"] == 2

    def test_marcador_tem_anel_na_cor_da_superficie(self, renderizador):
        """O anel mantem o marcador legivel onde as series se cruzam."""
        marcador = renderizador.renderizar(especificacao(TipoGrafico.LINHA))["data"][0]["marker"]
        assert marcador["size"] >= 8
        assert marcador["line"] == {"width": 2, "color": paleta.SUPERFICIE}

    def test_barra_tem_ponta_arredondada(self, renderizador):
        marcador = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))["data"][0][
            "marker"
        ]
        assert marcador["cornerradius"] == 4

    def test_barra_nao_tem_contorno(self, renderizador):
        """A separacao entre marcas e o vao de superficie, nunca um traco."""
        marcador = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))["data"][0][
            "marker"
        ]
        assert marcador["line"]["width"] == 0

    def test_barras_deixam_vao_entre_si(self, renderizador):
        figura = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))
        assert figura["layout"]["bargap"] > 0

    @pytest.mark.parametrize("categorias", [3, 10, 15])
    @pytest.mark.parametrize(
        "tipo", [TipoGrafico.BARRA_VERTICAL, TipoGrafico.BARRA_HORIZONTAL]
    )
    def test_espessura_da_marca_respeita_o_teto(self, renderizador, tipo, categorias):
        """Sem cap explicito, 15 UFs davam colunas de 33px e 3 barras davam 12px."""
        series = (Serie(tuple(LinhaResultado(f"B{i}", float(i + 1)) for i in range(categorias))),)
        figura = renderizador.renderizar(especificacao(tipo, series))

        if tipo is TipoGrafico.BARRA_HORIZONTAL:
            extensao = figura["layout"]["height"] - paleta.CHROME_VERTICAL
        else:
            extensao = paleta.LARGURA_PLOT_TIPICA

        espessura = (extensao / categorias) * figura["data"][0]["width"]
        assert espessura <= paleta.ESPESSURA_MAX
        assert espessura >= 12, "marca fina demais para ser lida"


class TestCorPorCategoria:
    def test_cada_barra_do_ranking_leva_a_cor_da_instituicao(self, renderizador):
        traco = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))["data"][0]
        assert list(traco["marker"]["color"]) == ["#CC092F", "#EC7000", "#E8B500"]

    def test_barra_horizontal_inverte_cor_junto_com_o_dado(self, renderizador):
        """Sem inverter, a cor deixaria de acompanhar o banco."""
        figura = renderizador.renderizar(especificacao(TipoGrafico.BARRA_HORIZONTAL))
        traco = figura["data"][0]
        assert list(traco["y"]) == ["BB", "ITAU", "BRADESCO"]
        assert list(traco["marker"]["color"]) == ["#E8B500", "#EC7000", "#CC092F"]

    def test_serie_temporal_mantem_uma_cor_por_serie(self, renderizador):
        """Na linha a cor identifica a serie; nao pode virar rotulo de ponto."""
        traco = renderizador.renderizar(especificacao(TipoGrafico.LINHA))["data"][0]
        assert traco["line"]["color"] == paleta.SERIES[0]

    def test_comparativo_mantem_uma_cor_por_serie(self, renderizador):
        comparativo = (
            Serie((LinhaResultado("a", 1.0), LinhaResultado("b", 2.0)), "SP"),
            Serie((LinhaResultado("a", 3.0), LinhaResultado("b", 4.0)), "RJ"),
        )
        figura = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL, comparativo))
        assert figura["data"][0]["marker"]["color"] == paleta.SERIES[0]
        assert figura["data"][1]["marker"]["color"] == paleta.SERIES[1]


class TestRotulosDeValor:
    def test_barra_leva_o_valor_na_ponta(self, renderizador):
        """Sem rotulo, so o hover diz quanto vale cada barra."""
        traco = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))["data"][0]
        assert list(traco["text"]) == ["R$ 300", "R$ 200", "R$ 100"]
        assert traco["textposition"] == "outside"

    def test_valores_grandes_saem_compactos(self, renderizador):
        """'R$ 1.022.240.653,99' nao cabe na ponta de uma barra."""
        series = (Serie((LinhaResultado("BRADESCO", 1022240653.99),)),)
        traco = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL, series))["data"][0]
        assert traco["text"][0] == "R$ 1,0 bi"

    def test_rotulo_usa_tinta_e_nunca_a_cor_do_dado(self, renderizador):
        traco = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))["data"][0]
        assert traco["textfont"]["color"] == paleta.INK_SECUNDARIO
        assert traco["textfont"]["color"] not in paleta.SERIES

    def test_linha_rotula_apenas_o_ultimo_ponto(self, renderizador):
        """Um numero em cada ponto de 34 meses seria ilegivel."""
        traco = renderizador.renderizar(especificacao(TipoGrafico.LINHA))["data"][0]
        assert list(traco["text"]) == ["", "", "R$ 100"]

    def test_eixo_some_quando_toda_marca_esta_rotulada(self, renderizador):
        """A escala repetiria o que a ponta da barra ja diz."""
        layout = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))["layout"]
        assert layout["yaxis"]["visible"] is False

    def test_linha_mantem_a_escala(self, renderizador):
        """So o fim foi rotulado; a grade carrega os outros 33 pontos."""
        layout = renderizador.renderizar(especificacao(TipoGrafico.LINHA))["layout"]
        assert layout["yaxis"]["visible"] is True

    def test_rotulo_nao_e_cortado_pela_borda(self, renderizador):
        traco = renderizador.renderizar(especificacao(TipoGrafico.BARRA_HORIZONTAL))["data"][0]
        assert traco["cliponaxis"] is False


class TestFormatoBrasileiro:
    def test_separadores_seguem_o_padrao_brasileiro(self, renderizador):
        """Sem isto o Plotly escreve 736,172.00 -- virgula e ponto trocados."""
        layout = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))["layout"]
        assert layout["separators"] == ",."

    def test_volume_tem_centavos_no_hover(self, renderizador):
        traco = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))["data"][0]
        assert "R$ %{y:,.2f}" in traco["hovertemplate"]

    def test_operacoes_nao_tem_centavos(self, renderizador):
        """Contagem nao admite fracao: '736.172,00 operacoes' seria absurdo."""
        spec = EspecificacaoGrafico(
            tipo=TipoGrafico.BARRA_VERTICAL,
            titulo="Operacoes por UF",
            rotulo_categoria="UF",
            rotulo_valor="Numero de operacoes",
            series=(Serie(LINHAS),),
            metrica=Metrica.NUMERO_OPERACOES,
        )
        traco = renderizador.renderizar(spec)["data"][0]
        assert "%{y:,.0f} operacoes" in traco["hovertemplate"]
        assert "R$" not in traco["hovertemplate"]

    def test_eixo_de_valor_arredonda_os_ticks(self, renderizador):
        eixo = renderizador.renderizar(especificacao(TipoGrafico.LINHA))["layout"]["yaxis"]
        assert eixo["tickformat"] == ",.0f"
        assert eixo["tickprefix"] == "R$ "


class TestChromeRecessivo:
    def test_grade_e_hairline_solida(self, renderizador):
        eixo = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))["layout"]["yaxis"]
        assert eixo["gridcolor"] == paleta.GRADE
        assert eixo["gridwidth"] == 1
        assert eixo["griddash"] == "solid"

    def test_texto_usa_tokens_de_tinta_e_nunca_a_cor_da_serie(self, renderizador):
        layout = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))["layout"]
        assert layout["title"]["font"]["color"] == paleta.INK_SECUNDARIO
        assert layout["yaxis"]["tickfont"]["color"] == paleta.INK_MUTED
        assert layout["title"]["font"]["color"] not in paleta.SERIES

    def test_fundo_do_grafico_e_a_superficie_declarada(self, renderizador):
        layout = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL))["layout"]
        assert layout["plot_bgcolor"] == paleta.SUPERFICIE
        assert layout["paper_bgcolor"] == paleta.SUPERFICIE


class TestAltura:
    def test_barra_horizontal_cresce_com_as_categorias(self, renderizador):
        """Altura fixa deixaria 3 barras gordas e 15 espremidas."""
        curta = renderizador.renderizar(especificacao(TipoGrafico.BARRA_HORIZONTAL))
        longa = renderizador.renderizar(
            especificacao(
                TipoGrafico.BARRA_HORIZONTAL,
                (Serie(tuple(LinhaResultado(f"B{i}", float(i)) for i in range(15))),),
            )
        )
        assert longa["layout"]["height"] > curta["layout"]["height"]


class TestMultiSerie:
    @pytest.fixture
    def comparativo(self):
        return (
            Serie((LinhaResultado("jan", 10.0), LinhaResultado("fev", 12.0)), "SP"),
            Serie((LinhaResultado("jan", 4.0), LinhaResultado("fev", 5.0)), "RJ"),
        )

    def test_um_traco_por_serie(self, renderizador, comparativo):
        figura = renderizador.renderizar(especificacao(TipoGrafico.LINHA, comparativo))
        assert len(figura["data"]) == 2
        assert [traco["name"] for traco in figura["data"]] == ["SP", "RJ"]

    def test_series_recebem_slots_da_paleta_em_ordem(self, renderizador, comparativo):
        figura = renderizador.renderizar(especificacao(TipoGrafico.LINHA, comparativo))
        cores = [traco["line"]["color"] for traco in figura["data"]]
        assert cores == [paleta.SERIES[0], paleta.SERIES[1]]

    def test_hover_identifica_a_serie_quando_ha_mais_de_uma(self, renderizador, comparativo):
        figura = renderizador.renderizar(especificacao(TipoGrafico.LINHA, comparativo))
        assert "<extra>SP</extra>" in figura["data"][0]["hovertemplate"]

    def test_comparativo_liga_a_legenda(self, renderizador, comparativo):
        figura = renderizador.renderizar(especificacao(TipoGrafico.LINHA, comparativo))
        assert figura["layout"]["showlegend"] is True

    def test_barras_comparativas_ficam_agrupadas(self, renderizador, comparativo):
        figura = renderizador.renderizar(especificacao(TipoGrafico.BARRA_VERTICAL, comparativo))
        assert figura["layout"]["barmode"] == "group"
