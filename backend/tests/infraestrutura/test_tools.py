import pytest

from aplicacao.consultar_desenrola import ConsultarDesenrolaUseCase
from infraestrutura.plotly_renderer import RenderizadorPlotly
from infraestrutura.tools import NOME_TOOL, criar_tool_consulta


@pytest.fixture
def ferramenta(repositorio):
    caso_de_uso = ConsultarDesenrolaUseCase(repositorio, RenderizadorPlotly())
    return criar_tool_consulta(caso_de_uso)


def invocar(ferramenta, **argumentos):
    return ferramenta.invoke(
        {"name": NOME_TOOL, "args": argumentos, "id": "chamada-1", "type": "tool_call"}
    )


class TestToolConsulta:
    def test_expoe_o_esquema_de_argumentos_ao_llm(self, ferramenta):
        campos = ferramenta.args_schema.model_fields
        assert "agrupar_por" in campos
        assert "grafico" not in campos, "o tipo de grafico e decisao do dominio, nao do LLM"

    def test_devolve_resumo_textual_e_artefato(self, ferramenta):
        mensagem = invocar(ferramenta, agrupar_por="conglomerado")
        assert "BB" in mensagem.content
        assert mensagem.artifact["grafico"] is not None
        assert mensagem.artifact["resultado"] is not None

    def test_traduz_uf_por_extenso(self, ferramenta):
        mensagem = invocar(ferramenta, agrupar_por="conglomerado", ufs=["São Paulo"])
        assert "BB" in mensagem.content

    def test_unifica_conglomerado_com_sufixo_prudencial(self, ferramenta):
        mensagem = invocar(ferramenta, agrupar_por="periodo", conglomerados=["BB - PRUDENCIAL"])
        assert "dez/2023" in mensagem.content

    def test_consulta_de_uma_linha_nao_traz_grafico(self, ferramenta):
        mensagem = invocar(ferramenta, agrupar_por="conglomerado", ufs=["RJ"])
        assert mensagem.artifact["grafico"] is None

    def test_argumento_invalido_volta_como_texto_para_o_modelo(self, ferramenta):
        """Erro legivel deixa o LLM se corrigir; excecao derrubaria a requisicao."""
        mensagem = invocar(ferramenta, agrupar_por="conglomerado", ufs=["XX"])
        assert "invalido" in mensagem.content.lower()
        assert mensagem.artifact == {}

    def test_intervalo_invertido_volta_como_texto(self, ferramenta):
        mensagem = invocar(
            ferramenta, agrupar_por="periodo", periodo_inicio=202501, periodo_fim=202312
        )
        assert "invalido" in mensagem.content.lower()

    def test_duas_dimensoes_de_comparacao_voltam_como_texto(self, ferramenta):
        mensagem = invocar(
            ferramenta, agrupar_por="periodo", ufs=["SP", "RJ"], conglomerados=["BB", "BRADESCO"]
        )
        assert "invalido" in mensagem.content.lower()

    def test_limite_produz_ranking_curto(self, ferramenta):
        mensagem = invocar(ferramenta, agrupar_por="conglomerado", limite=1)
        assert "1. BB" in mensagem.content
        assert "2. " not in mensagem.content


class TestComparacaoNumaChamadaSo:
    def test_duas_ufs_geram_um_unico_grafico_com_duas_series(self, ferramenta):
        """Antes o modelo fazia duas chamadas e o segundo grafico apagava o primeiro."""
        mensagem = invocar(ferramenta, agrupar_por="periodo", ufs=["SP", "RJ"])
        assert len(mensagem.artifact["grafico"]["data"]) == 2
        assert mensagem.artifact["resultado"].comparativo

    def test_resumo_identifica_cada_serie(self, ferramenta):
        mensagem = invocar(ferramenta, agrupar_por="periodo", ufs=["SP", "RJ"])
        assert "SP:" in mensagem.content
        assert "RJ:" in mensagem.content
