"""Testes da fronteira HTTP com agente falso -- nenhuma chamada de rede."""

import pytest
from fastapi.testclient import TestClient

from aplicacao.responder_pergunta import ResponderPerguntaUseCase
from dominio.consulta import LinhaResultado, ResultadoConsulta
from dominio.dimensao import Dimensao
from dominio.metrica import Metrica
from dominio.portas import RespostaAgente
from infraestrutura.api import criar_aplicacao, obter_responder
from infraestrutura.settings import Settings
from tests.aplicacao.fakes import AgenteFake


@pytest.fixture
def csv_temporario(tmp_path):
    from tests.infraestrutura.conftest import CSV_SINTETICO

    caminho = tmp_path / "desenrola.csv"
    caminho.write_text(CSV_SINTETICO, encoding="utf-8")
    return caminho


@pytest.fixture
def cliente(csv_temporario):
    """Sem GROQ_API_KEY: a aplicacao sobe e /api/chat responde 503."""
    app = criar_aplicacao(Settings(csv_path=csv_temporario, groq_api_key=""))
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture
def cliente_com_agente(cliente):
    agente = AgenteFake(
        RespostaAgente(
            texto="O BB lidera em Sao Paulo.",
            graficos=({"data": [], "layout": {}},),
            resultados=(
                ResultadoConsulta.de_linhas(
                    (LinhaResultado("BB", 1000.5),), Dimensao.CONGLOMERADO, Metrica.VOLUME
                ),
            ),
        )
    )
    cliente.app.dependency_overrides[obter_responder] = lambda: ResponderPerguntaUseCase(agente)
    yield cliente
    cliente.app.dependency_overrides.clear()


class TestSaude:
    def test_informa_o_estado_do_conjunto_de_dados(self, cliente):
        corpo = cliente.get("/api/saude").json()
        assert corpo["status"] == "ok"
        assert corpo["registros"] == 7
        assert corpo["periodo"] == "dez/2023 a jan/2025"

    def test_sinaliza_agente_indisponivel_sem_chave(self, cliente):
        assert cliente.get("/api/saude").json()["agente_disponivel"] is False


class TestBase:
    def test_descreve_a_origem_dos_dados(self, cliente):
        corpo = cliente.get("/api/base").json()
        assert "Banco Central" in corpo["fonte"]
        assert corpo["url"].endswith("dados_desenrola.csv")

    def test_sintetiza_a_cobertura(self, cliente):
        corpo = cliente.get("/api/base").json()
        assert corpo["periodo"] == "dez/2023 a jan/2025"
        assert corpo["meses"] == 2
        assert corpo["registros"] == 7
        assert corpo["conglomerados"] == 3
        assert corpo["ufs"] == 2

    def test_soma_os_totais(self, cliente):
        corpo = cliente.get("/api/base").json()
        assert corpo["volume_total"] == pytest.approx(3300.75)
        assert corpo["operacoes_totais"] == 330

    def test_descreve_cada_modalidade_para_o_glossario(self, cliente):
        modalidades = cliente.get("/api/base").json()["modalidades"]
        assert [m["nome"] for m in modalidades] == ["Faixa 1", "Faixa 2", "Pequenos Negocios"]

        faixa_1 = modalidades[0]
        assert "CadUnico" in faixa_1["publico"]
        assert "R$ 5 mil" in faixa_1["teto"]
        assert "FGO" in faixa_1["garantia"]
        assert faixa_1["base_legal"] == "Lei 14.690/2023"

    def test_modalidade_usa_a_mesma_cor_do_grafico(self, cliente):
        """O glossario e as barras agrupadas por modalidade precisam concordar."""
        from infraestrutura import paleta

        cores = [m["cor"] for m in cliente.get("/api/base").json()["modalidades"]]
        assert cores == list(paleta.SERIES[:3])

    def test_entrega_o_dicionario_oficial_de_colunas(self, cliente):
        colunas = cliente.get("/api/base").json()["colunas"]
        assert "AAAAMM" in colunas["DATA_BASE"]
        assert "VOLUME_OPERACOES" in colunas


class TestChat:
    def test_responde_com_texto_graficos_e_tabelas(self, cliente_com_agente):
        resposta = cliente_com_agente.post("/api/chat", json={"pergunta": "quem lidera em SP?"})
        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["resposta"] == "O BB lidera em Sao Paulo."
        assert corpo["graficos"] == [{"data": [], "layout": {}}]
        tabela = corpo["tabelas"][0]
        assert tabela["linhas"] == [
            {"rotulo": "BB", "valores": {"Volume renegociado (R$)": 1000.5}}
        ]

    def test_tabela_traz_os_dados_completos_para_o_front(self, cliente_com_agente):
        """A tabela vem da fonte, nao da transcricao do modelo."""
        corpo = cliente_com_agente.post("/api/chat", json={"pergunta": "oi"}).json()
        assert corpo["tabelas"][0]["dimensao"] == "Conglomerado financeiro"

    def test_sem_chave_configurada_responde_503_com_instrucao(self, cliente):
        resposta = cliente.post("/api/chat", json={"pergunta": "oi"})
        assert resposta.status_code == 503
        assert "GROQ_API_KEY" in resposta.json()["detail"]

    def test_pergunta_vazia_e_rejeitada_na_validacao(self, cliente_com_agente):
        assert cliente_com_agente.post("/api/chat", json={"pergunta": ""}).status_code == 422

    def test_pergunta_longa_demais_e_rejeitada(self, cliente_com_agente):
        resposta = cliente_com_agente.post("/api/chat", json={"pergunta": "a" * 501})
        assert resposta.status_code == 422

    def test_falha_do_provedor_vira_502_sem_vazar_detalhe(self, cliente):
        class AgenteQueFalha:
            def responder(self, pergunta):
                raise RuntimeError("connection reset by peer")

        cliente.app.dependency_overrides[obter_responder] = lambda: ResponderPerguntaUseCase(
            AgenteQueFalha()
        )
        resposta = cliente.post("/api/chat", json={"pergunta": "oi"})
        cliente.app.dependency_overrides.clear()

        assert resposta.status_code == 502
        assert "connection reset" not in resposta.text


class TestCors:
    def test_libera_a_origem_do_frontend(self, cliente):
        resposta = cliente.options(
            "/api/chat",
            headers={
                "Origin": "http://localhost:4200",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resposta.headers["access-control-allow-origin"] == "http://localhost:4200"
