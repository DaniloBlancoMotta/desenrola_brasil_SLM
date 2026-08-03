import pytest

from dominio.conglomerado import Conglomerado
from dominio.consulta import ConsultaDesenrola
from dominio.dimensao import Dimensao
from dominio.metrica import Metrica
from dominio.periodo import Periodo
from dominio.tipo_desenrola import TipoDesenrola
from dominio.unidade_federacao import UnidadeFederacao

SP = UnidadeFederacao("SP")
RJ = UnidadeFederacao("RJ")
BB = Conglomerado.de_bruto("BB")


class TestNormalizacao:
    def test_unifica_banco_atraves_da_virada_de_2025(self, repositorio):
        """BB (ate 2024) e BB - PRUDENCIAL (de 2025) sao a mesma instituicao."""
        resultado = repositorio.consultar(ConsultaDesenrola(agrupar_por=Dimensao.CONGLOMERADO))
        rotulos = [linha.rotulo for linha in resultado.linhas]
        assert "BB" in rotulos
        assert "BB - PRUDENCIAL" not in rotulos

    def test_soma_atravessa_a_virada(self, repositorio):
        """Sem unificacao o BB apareceria com 1300,50 em vez de 2500,50."""
        resultado = repositorio.consultar(
            ConsultaDesenrola(agrupar_por=Dimensao.CONGLOMERADO, conglomerados=(BB,))
        )
        assert resultado.linhas[0].valor == pytest.approx(2500.50)

    def test_filtro_por_conglomerado_alcanca_ambas_as_grafias(self, repositorio):
        consulta = ConsultaDesenrola(
            agrupar_por=Dimensao.PERIODO,
            conglomerados=(Conglomerado.de_bruto("BB - PRUDENCIAL"),),
        )
        assert len(repositorio.consultar(consulta).linhas) == 2


class TestAgregacao:
    def test_agrupa_por_uf(self, repositorio):
        resultado = repositorio.consultar(ConsultaDesenrola(agrupar_por=Dimensao.UF))
        por_uf = {linha.rotulo: linha.valor for linha in resultado.linhas}
        assert por_uf["SP"] == pytest.approx(2600.75)
        assert por_uf["RJ"] == pytest.approx(700.00)

    def test_ordena_ranking_do_maior_para_o_menor(self, repositorio):
        resultado = repositorio.consultar(ConsultaDesenrola(agrupar_por=Dimensao.UF))
        valores = [linha.valor for linha in resultado.linhas]
        assert valores == sorted(valores, reverse=True)

    def test_serie_temporal_sai_em_ordem_cronologica(self, repositorio):
        resultado = repositorio.consultar(ConsultaDesenrola(agrupar_por=Dimensao.PERIODO))
        assert [linha.rotulo for linha in resultado.linhas] == ["dez/2023", "jan/2025"]

    def test_metrica_alternativa_conta_operacoes(self, repositorio):
        resultado = repositorio.consultar(
            ConsultaDesenrola(agrupar_por=Dimensao.UF, metrica=Metrica.NUMERO_OPERACOES)
        )
        por_uf = {linha.rotulo: linha.valor for linha in resultado.linhas}
        assert por_uf["SP"] == 260

    def test_rotula_tipo_com_a_descricao_da_modalidade(self, repositorio):
        resultado = repositorio.consultar(ConsultaDesenrola(agrupar_por=Dimensao.TIPO))
        assert "Pequenos Negocios" in {linha.rotulo for linha in resultado.linhas}


class TestComparacaoDeSeries:
    def test_duas_ufs_ao_longo_do_tempo_viram_duas_series(self, repositorio):
        resultado = repositorio.consultar(
            ConsultaDesenrola(agrupar_por=Dimensao.PERIODO, ufs=(SP, RJ))
        )
        assert resultado.comparativo
        assert [serie.nome for serie in resultado.series] == ["SP", "RJ"]

    def test_cada_serie_traz_os_proprios_valores(self, repositorio):
        resultado = repositorio.consultar(
            ConsultaDesenrola(agrupar_por=Dimensao.PERIODO, ufs=(SP, RJ))
        )
        sp, rj = resultado.series
        assert {linha.rotulo: linha.valor for linha in sp.linhas}["dez/2023"] == pytest.approx(
            1700.75
        )
        assert {linha.rotulo: linha.valor for linha in rj.linhas}["dez/2023"] == pytest.approx(
            300.00
        )

    def test_preserva_a_ordem_pedida_das_series(self, repositorio):
        resultado = repositorio.consultar(
            ConsultaDesenrola(agrupar_por=Dimensao.PERIODO, ufs=(RJ, SP))
        )
        assert [serie.nome for serie in resultado.series] == ["RJ", "SP"]

    def test_conglomerados_comparados_usam_o_nome_de_exibicao(self, repositorio):
        resultado = repositorio.consultar(
            ConsultaDesenrola(
                agrupar_por=Dimensao.PERIODO,
                conglomerados=(BB, Conglomerado.de_bruto("BRADESCO")),
            )
        )
        assert [serie.nome for serie in resultado.series] == ["BB", "BRADESCO"]

    def test_agrupar_por_uf_com_varias_ufs_continua_serie_unica(self, repositorio):
        """Restringir um ranking a dois estados nao e comparar series."""
        resultado = repositorio.consultar(
            ConsultaDesenrola(agrupar_por=Dimensao.UF, ufs=(SP, RJ))
        )
        assert not resultado.comparativo
        assert len(resultado.linhas) == 2

    def test_serie_sem_dados_e_omitida(self, repositorio):
        resultado = repositorio.consultar(
            ConsultaDesenrola(
                agrupar_por=Dimensao.PERIODO, ufs=(SP, UnidadeFederacao("AC"))
            )
        )
        assert [serie.nome for serie in resultado.series] == ["SP"]


class TestFiltros:
    def test_filtra_por_uf(self, repositorio):
        resultado = repositorio.consultar(
            ConsultaDesenrola(agrupar_por=Dimensao.CONGLOMERADO, ufs=(RJ,))
        )
        assert [linha.rotulo for linha in resultado.linhas] == ["BB"]

    def test_filtra_por_tipo(self, repositorio):
        resultado = repositorio.consultar(
            ConsultaDesenrola(
                agrupar_por=Dimensao.CONGLOMERADO, tipo=TipoDesenrola.PEQUENOS_NEGOCIOS
            )
        )
        assert [linha.rotulo for linha in resultado.linhas] == ["BRADESCO"]

    def test_filtra_por_intervalo_de_periodo(self, repositorio):
        resultado = repositorio.consultar(
            ConsultaDesenrola(
                agrupar_por=Dimensao.PERIODO, periodo_inicio=Periodo.de_aaaamm(202501)
            )
        )
        assert [linha.rotulo for linha in resultado.linhas] == ["jan/2025"]

    def test_filtro_sem_correspondencia_devolve_resultado_vazio(self, repositorio):
        resultado = repositorio.consultar(
            ConsultaDesenrola(
                agrupar_por=Dimensao.CONGLOMERADO, ufs=(UnidadeFederacao("AC"),)
            )
        )
        assert resultado.vazio

    def test_limite_trunca_e_registra_o_total(self, repositorio):
        resultado = repositorio.consultar(
            ConsultaDesenrola(agrupar_por=Dimensao.CONGLOMERADO, limite=1)
        )
        assert len(resultado.linhas) == 1
        assert resultado.total_de_grupos == 3
        assert resultado.foi_truncado


class TestCatalogo:
    def test_lista_conglomerados_por_relevancia(self, repositorio):
        """O corte no system prompt precisa preservar os bancos que importam."""
        assert repositorio.catalogo().conglomerados[0] == "BB"

    def test_expoe_intervalo_de_datas(self, repositorio):
        catalogo = repositorio.catalogo()
        assert str(catalogo.periodo_inicio) == "dez/2023"
        assert str(catalogo.periodo_fim) == "jan/2025"

    def test_rejeita_arquivo_inexistente(self, tmp_path):
        from infraestrutura.csv_repository import RepositorioDesenrolaCSV

        with pytest.raises(FileNotFoundError):
            RepositorioDesenrolaCSV(tmp_path / "nao_existe.csv")


class TestDadosReais:
    def test_carrega_o_csv_do_banco_central(self, repositorio_real):
        catalogo = repositorio_real.catalogo()
        assert len(catalogo.ufs) == 27
        assert str(catalogo.periodo_inicio) == "set/2023"

    def test_bb_tem_serie_continua_sem_buraco_em_2025(self, repositorio_real):
        """Regressao da armadilha PRUDENCIAL contra o arquivo oficial."""
        resultado = repositorio_real.consultar(
            ConsultaDesenrola(agrupar_por=Dimensao.PERIODO, conglomerados=(BB,))
        )
        meses_de_2025 = [linha for linha in resultado.linhas if "2025" in linha.rotulo]
        assert len(meses_de_2025) == 12
        assert all(linha.valor > 0 for linha in meses_de_2025)

    def test_todas_as_27_ufs_saem_na_consulta_sem_limite(self, repositorio_real):
        resultado = repositorio_real.consultar(
            ConsultaDesenrola(agrupar_por=Dimensao.UF, metrica=Metrica.NUMERO_OPERACOES)
        )
        assert len(resultado.linhas) == 27

    def test_comparacao_sp_rj_cobre_os_34_meses(self, repositorio_real):
        """O caso que antes exigia duas chamadas e perdia um dos graficos."""
        resultado = repositorio_real.consultar(
            ConsultaDesenrola(
                agrupar_por=Dimensao.PERIODO,
                metrica=Metrica.NUMERO_OPERACOES,
                ufs=(SP, RJ),
            )
        )
        assert resultado.comparativo
        assert all(len(serie.linhas) == 34 for serie in resultado.series)
        assert resultado.series[0].linhas[-1].rotulo == "jun/2026"
