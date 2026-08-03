import pytest

from dominio.conglomerado import Conglomerado
from dominio.consulta import ConsultaDesenrola, LinhaResultado, ResultadoConsulta, Serie
from dominio.dimensao import Dimensao
from dominio.metrica import Metrica
from dominio.periodo import Periodo
from dominio.tipo_desenrola import TipoDesenrola
from dominio.unidade_federacao import UnidadeFederacao

SP = UnidadeFederacao("SP")
RJ = UnidadeFederacao("RJ")


class TestConsultaDesenrola:
    def test_rejeita_intervalo_invertido(self):
        with pytest.raises(ValueError, match="posterior"):
            ConsultaDesenrola(
                agrupar_por=Dimensao.PERIODO,
                periodo_inicio=Periodo.de_aaaamm(202412),
                periodo_fim=Periodo.de_aaaamm(202301),
            )

    def test_rejeita_limite_nao_positivo(self):
        with pytest.raises(ValueError, match="positivo"):
            ConsultaDesenrola(agrupar_por=Dimensao.UF, limite=0)

    def test_rejeita_duas_dimensoes_de_comparacao(self):
        """Series cruzadas dariam um produto cartesiano ilegivel."""
        with pytest.raises(ValueError, match="nao os dois"):
            ConsultaDesenrola(
                agrupar_por=Dimensao.PERIODO,
                ufs=(SP, RJ),
                conglomerados=(Conglomerado.de_bruto("BB"), Conglomerado.de_bruto("ITAU")),
            )

    def test_descreve_filtros_para_o_titulo(self):
        consulta = ConsultaDesenrola(
            agrupar_por=Dimensao.CONGLOMERADO,
            ufs=(SP,),
            tipo=TipoDesenrola.FAIXA_1,
        )
        assert consulta.descricao_filtros == "Sao Paulo, Faixa 1 (pessoas fisicas)"

    def test_descreve_comparacao_com_separador(self):
        consulta = ConsultaDesenrola(agrupar_por=Dimensao.PERIODO, ufs=(SP, RJ))
        assert consulta.descricao_filtros == "Sao Paulo x Rio de Janeiro"

    def test_sem_filtros_descreve_vazio(self):
        assert ConsultaDesenrola(agrupar_por=Dimensao.UF).descricao_filtros == ""


class TestDimensaoDeComparacao:
    def test_varias_ufs_ao_longo_do_tempo_separam_series(self):
        consulta = ConsultaDesenrola(agrupar_por=Dimensao.PERIODO, ufs=(SP, RJ))
        assert consulta.dimensao_de_comparacao is Dimensao.UF

    def test_uma_uf_nao_gera_comparacao(self):
        consulta = ConsultaDesenrola(agrupar_por=Dimensao.PERIODO, ufs=(SP,))
        assert consulta.dimensao_de_comparacao is None

    def test_agrupar_pela_propria_dimensao_e_apenas_filtro(self):
        """Ranking de UFs restrito a duas continua sendo ranking, nao comparacao."""
        consulta = ConsultaDesenrola(agrupar_por=Dimensao.UF, ufs=(SP, RJ))
        assert consulta.dimensao_de_comparacao is None

    def test_varios_conglomerados_ao_longo_do_tempo_separam_series(self):
        consulta = ConsultaDesenrola(
            agrupar_por=Dimensao.PERIODO,
            conglomerados=(Conglomerado.de_bruto("BB"), Conglomerado.de_bruto("ITAU")),
        )
        assert consulta.dimensao_de_comparacao is Dimensao.CONGLOMERADO


class TestResultadoConsulta:
    def test_sinaliza_truncamento(self):
        resultado = ResultadoConsulta.de_linhas(
            (LinhaResultado("BB", 10.0),),
            Dimensao.CONGLOMERADO,
            Metrica.VOLUME,
            total_de_grupos=64,
        )
        assert resultado.foi_truncado

    def test_soma_o_total(self):
        resultado = ResultadoConsulta.de_linhas(
            (LinhaResultado("BB", 10.0), LinhaResultado("ITAU", 5.0)),
            Dimensao.CONGLOMERADO,
            Metrica.VOLUME,
        )
        assert resultado.total == 15.0
        assert not resultado.foi_truncado

    def test_linhas_e_atalho_da_serie_unica(self):
        resultado = ResultadoConsulta.de_linhas(
            (LinhaResultado("BB", 10.0),), Dimensao.CONGLOMERADO, Metrica.VOLUME
        )
        assert not resultado.comparativo
        assert resultado.linhas[0].rotulo == "BB"

    def test_multi_serie_soma_todas_as_series(self):
        resultado = ResultadoConsulta(
            series=(
                Serie((LinhaResultado("jan", 10.0),), "SP"),
                Serie((LinhaResultado("jan", 4.0),), "RJ"),
            ),
            dimensao=Dimensao.PERIODO,
            metrica=Metrica.VOLUME,
        )
        assert resultado.comparativo
        assert resultado.total == 14.0
        assert resultado.maior_serie == 1

    def test_resultado_sem_series_e_vazio(self):
        vazio = ResultadoConsulta(series=(), dimensao=Dimensao.UF, metrica=Metrica.VOLUME)
        assert vazio.vazio
        assert vazio.linhas == ()
