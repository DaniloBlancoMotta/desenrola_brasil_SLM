import pytest

from dominio.consulta import LinhaResultado, ResultadoConsulta, Serie
from dominio.dimensao import Dimensao
from dominio.metrica import Metrica
from dominio.visualizacao import (
    LIMITE_CATEGORIAS,
    LIMITE_SERIES,
    PoliticaVisualizacao,
    TipoGrafico,
)


def resultado(dimensao: Dimensao, quantidade: int) -> ResultadoConsulta:
    linhas = tuple(LinhaResultado(f"item {i}", float(quantidade - i)) for i in range(quantidade))
    return ResultadoConsulta.de_linhas(linhas, dimensao, Metrica.VOLUME)


def comparativo(dimensao: Dimensao, nomes: tuple[str, ...], pontos: int) -> ResultadoConsulta:
    series = tuple(
        Serie(
            linhas=tuple(LinhaResultado(f"item {i}", float(pontos - i)) for i in range(pontos)),
            nome=nome,
        )
        for nome in nomes
    )
    return ResultadoConsulta(
        series=series, dimensao=dimensao, metrica=Metrica.VOLUME, total_de_grupos=pontos
    )


@pytest.fixture
def politica() -> PoliticaVisualizacao:
    return PoliticaVisualizacao()


class TestPoliticaVisualizacao:
    def test_resultado_de_uma_linha_nao_vira_grafico(self, politica):
        """A resposta e um numero; um grafico de uma barra so seria ruido."""
        assert politica.decidir(resultado(Dimensao.UF, 1)) is None

    def test_resultado_vazio_nao_vira_grafico(self, politica):
        vazio = ResultadoConsulta(series=(), dimensao=Dimensao.UF, metrica=Metrica.VOLUME)
        assert politica.decidir(vazio) is None

    def test_serie_temporal_vira_linha(self, politica):
        spec = politica.decidir(resultado(Dimensao.PERIODO, 12))
        assert spec is not None
        assert spec.tipo is TipoGrafico.LINHA

    def test_conglomerado_vira_barra_horizontal(self, politica):
        """Nomes longos ficam ilegiveis rotacionados no eixo x."""
        spec = politica.decidir(resultado(Dimensao.CONGLOMERADO, 5))
        assert spec.tipo is TipoGrafico.BARRA_HORIZONTAL

    def test_uf_vira_barra_vertical(self, politica):
        spec = politica.decidir(resultado(Dimensao.UF, 27))
        assert spec.tipo is TipoGrafico.BARRA_VERTICAL

    def test_poucas_categorias_viram_barra_horizontal(self, politica):
        """Tres colunas verticais viram blocos largos demais."""
        spec = politica.decidir(resultado(Dimensao.UF, 3))
        assert spec.tipo is TipoGrafico.BARRA_HORIZONTAL

    def test_modalidade_vira_barra_horizontal(self, politica):
        """'Faixa 1 (pessoas fisicas)' nao cabe rotacionado."""
        spec = politica.decidir(resultado(Dimensao.TIPO, 3))
        assert spec.tipo is TipoGrafico.BARRA_HORIZONTAL

    def test_ranking_colore_cada_barra(self, politica):
        spec = politica.decidir(resultado(Dimensao.CONGLOMERADO, 64))
        assert spec.cor_por_categoria
        assert spec.categorias_exibidas == LIMITE_CATEGORIAS

    def test_comparativo_colore_por_serie_e_nao_por_barra(self, politica):
        """Ali a cor ja identifica a serie e nao pode ser reaproveitada."""
        spec = politica.decidir(comparativo(Dimensao.CONGLOMERADO, ("SP", "RJ"), 64))
        assert not spec.cor_por_categoria
        assert spec.categorias_exibidas == LIMITE_CATEGORIAS

    def test_nao_trunca_serie_temporal(self, politica):
        """34 meses formam uma linha legivel; cortar esconderia a tendencia."""
        spec = politica.decidir(resultado(Dimensao.PERIODO, 34))
        assert len(spec.linhas) == 34

    def test_titulo_incorpora_filtros(self, politica):
        com_filtro = ResultadoConsulta.de_linhas(
            (LinhaResultado("BB", 10.0), LinhaResultado("ITAU", 5.0)),
            Dimensao.CONGLOMERADO,
            Metrica.VOLUME,
            descricao_filtros="Sao Paulo",
        )
        assert "Sao Paulo" in politica.decidir(com_filtro).titulo


class TestComparativo:
    def test_duas_series_temporais_viram_um_grafico_de_linhas(self, politica):
        spec = politica.decidir(comparativo(Dimensao.PERIODO, ("SP", "RJ"), 34))
        assert spec.tipo is TipoGrafico.LINHA
        assert spec.comparativo
        assert [serie.nome for serie in spec.series] == ["SP", "RJ"]

    def test_comparativo_de_um_ponto_ainda_vira_grafico(self, politica):
        """Comparar dois valores e o proposito; nao ha ruido em desenhar."""
        assert politica.decidir(comparativo(Dimensao.UF, ("SP", "RJ"), 1)) is not None

    def test_conglomerados_comparados_usam_barra_agrupada(self, politica):
        """Barras horizontais agrupadas confundem mais do que ajudam."""
        spec = politica.decidir(comparativo(Dimensao.TIPO, ("BB", "ITAU"), 3))
        assert spec.tipo is TipoGrafico.BARRA_VERTICAL

    def test_truncamento_preserva_as_mesmas_categorias_em_todas_as_series(self, politica):
        """Rotulos divergentes deixariam as barras agrupadas desalinhadas."""
        spec = politica.decidir(comparativo(Dimensao.CONGLOMERADO, ("SP", "RJ"), 40))
        rotulos = [tuple(linha.rotulo for linha in serie.linhas) for serie in spec.series]
        assert rotulos[0] == rotulos[1]
        assert len(rotulos[0]) == LIMITE_CATEGORIAS

    def test_corta_series_alem_do_teto_da_paleta(self, politica):
        """A nona serie nao ganha cor nova: a paleta tem ordem fixa e nao cicla."""
        nomes = tuple(f"UF{i}" for i in range(12))
        spec = politica.decidir(comparativo(Dimensao.PERIODO, nomes, 10))
        assert spec.series_exibidas == LIMITE_SERIES
