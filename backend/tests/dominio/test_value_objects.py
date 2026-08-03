import pytest

from dominio.conglomerado import Conglomerado
from dominio.metrica import Metrica
from dominio.periodo import Periodo
from dominio.tipo_desenrola import TipoDesenrola
from dominio.unidade_federacao import UnidadeFederacao


class TestPeriodo:
    def test_interpreta_aaaamm(self):
        periodo = Periodo.de_aaaamm(202309)
        assert (periodo.ano, periodo.mes) == (2023, 9)
        assert periodo.aaaamm == 202309

    def test_formata_para_leitura(self):
        assert str(Periodo.de_aaaamm(202309)) == "set/2023"

    def test_ordena_cronologicamente(self):
        assert Periodo.de_aaaamm(202412) < Periodo.de_aaaamm(202501)

    @pytest.mark.parametrize("invalido", [20239, "2023-09", 202313, "abcdef"])
    def test_rejeita_formato_invalido(self, invalido):
        with pytest.raises(ValueError):
            Periodo.de_aaaamm(invalido)


class TestConglomerado:
    def test_unifica_quebra_de_janeiro_2025(self):
        """O BCB trocou o codigo do conglomerado; a identidade vem do nome."""
        antes = Conglomerado.de_bruto("BB")
        depois = Conglomerado.de_bruto("BB - PRUDENCIAL")
        assert antes == depois

    def test_preserva_acento_na_exibicao_mas_nao_na_identidade(self):
        caixa = Conglomerado.de_bruto("CAIXA ECONÔMICA FEDERAL")
        assert caixa.nome_exibicao == "CAIXA ECONÔMICA FEDERAL"
        assert caixa.nome_canonico == "CAIXA ECONOMICA FEDERAL"

    def test_conglomerados_distintos_nao_colidem(self):
        assert Conglomerado.de_bruto("BB") != Conglomerado.de_bruto("BRADESCO")

    def test_serve_como_chave_de_agrupamento(self):
        agrupado = {Conglomerado.de_bruto("BB"), Conglomerado.de_bruto("BB - PRUDENCIAL")}
        assert len(agrupado) == 1


class TestUnidadeFederacao:
    def test_aceita_sigla(self):
        assert UnidadeFederacao.de_texto("sp").sigla == "SP"

    def test_aceita_nome_por_extenso_com_acento(self):
        assert UnidadeFederacao.de_texto("São Paulo").sigla == "SP"

    def test_expoe_nome_para_a_resposta(self):
        assert UnidadeFederacao("RJ").nome == "Rio de Janeiro"

    def test_rejeita_uf_inexistente(self):
        with pytest.raises(ValueError):
            UnidadeFederacao.de_texto("XX")


class TestMetrica:
    def test_formata_volume_no_padrao_brasileiro(self):
        """Virgula decimal e ponto de milhar."""
        assert Metrica.VOLUME.formatar(1418395.99) == "R$ 1.418.395,99"

    def test_formata_contagem_sem_centavos(self):
        assert Metrica.NUMERO_OPERACOES.formatar(1418) == "1.418 operacoes"

    def test_casas_decimais_seguem_a_natureza_da_medida(self):
        assert Metrica.VOLUME.casas_decimais == 2
        assert Metrica.NUMERO_OPERACOES.casas_decimais == 0

    @pytest.mark.parametrize(
        ("valor", "esperado"),
        [
            (2439623564.43, "R$ 2,4 bi"),
            (1022240653.99, "R$ 1,0 bi"),
            (867912345.0, "R$ 867,9 mi"),
            (24700.0, "R$ 24,7 mil"),
            (999.5, "R$ 1.000"),
        ],
    )
    def test_forma_compacta_usa_virgula_decimal(self, valor, esperado):
        assert Metrica.VOLUME.formatar_compacto(valor) == esperado

    def test_compacto_de_contagem_dispensa_o_prefixo_de_moeda(self):
        assert Metrica.NUMERO_OPERACOES.formatar_compacto(736172) == "736,2 mil"


class TestTipoDesenrola:
    def test_mapeia_codigo_do_csv(self):
        assert TipoDesenrola.de_codigo(3) is TipoDesenrola.PEQUENOS_NEGOCIOS

    def test_descreve_a_modalidade(self):
        assert "Pequenos Negocios" in TipoDesenrola.PEQUENOS_NEGOCIOS.descricao
