import pytest

from aplicacao.dtos import PerguntaDTO
from aplicacao.responder_pergunta import PerguntaInvalidaError, ResponderPerguntaUseCase
from dominio.consulta import LinhaResultado, ResultadoConsulta, Serie
from dominio.dimensao import Dimensao
from dominio.metrica import Metrica
from dominio.portas import RespostaAgente
from tests.aplicacao.fakes import AgenteFake


def resultado_simples() -> ResultadoConsulta:
    return ResultadoConsulta.de_linhas(
        (LinhaResultado("BB", 100.0), LinhaResultado("ITAU", 50.0)),
        Dimensao.CONGLOMERADO,
        Metrica.VOLUME,
    )


class TestResponderPergunta:
    def test_delega_a_pergunta_ao_agente(self):
        agente = AgenteFake()
        ResponderPerguntaUseCase(agente).executar(PerguntaDTO("Top 5 bancos em SP"))
        assert agente.perguntas == ["Top 5 bancos em SP"]

    def test_converte_resultado_do_dominio_em_tabela_serializavel(self):
        agente = AgenteFake(
            RespostaAgente(
                texto="O BB lidera.",
                graficos=({"tipo": "barra_horizontal"},),
                resultados=(resultado_simples(),),
            )
        )
        resposta = ResponderPerguntaUseCase(agente).executar(PerguntaDTO("quem lidera?"))
        assert resposta.resposta == "O BB lidera."
        assert resposta.graficos == [{"tipo": "barra_horizontal"}]
        tabela = resposta.tabelas[0]
        assert tabela.linhas[0] == {"rotulo": "BB", "valores": {"Volume renegociado (R$)": 100.0}}

    def test_tabela_comparativa_agrupa_series_por_rotulo(self):
        """A tabela precisa de uma coluna por serie para o front pivotar."""
        comparativo = ResultadoConsulta(
            series=(
                Serie((LinhaResultado("jan/2024", 10.0),), "SP"),
                Serie((LinhaResultado("jan/2024", 4.0),), "RJ"),
            ),
            dimensao=Dimensao.PERIODO,
            metrica=Metrica.VOLUME,
        )
        agente = AgenteFake(RespostaAgente(texto="ok", resultados=(comparativo,)))
        tabela = ResponderPerguntaUseCase(agente).executar(PerguntaDTO("SP x RJ")).tabelas[0]
        assert tabela.series == ["SP", "RJ"]
        assert tabela.linhas == [{"rotulo": "jan/2024", "valores": {"SP": 10.0, "RJ": 4.0}}]

    def test_multiplas_consultas_geram_multiplas_tabelas_e_graficos(self):
        agente = AgenteFake(
            RespostaAgente(
                texto="ok",
                graficos=({"a": 1}, {"b": 2}),
                resultados=(resultado_simples(), resultado_simples()),
            )
        )
        resposta = ResponderPerguntaUseCase(agente).executar(PerguntaDTO("duas coisas"))
        assert len(resposta.graficos) == 2
        assert len(resposta.tabelas) == 2

    def test_sem_consulta_os_campos_ficam_vazios(self):
        resposta = ResponderPerguntaUseCase(AgenteFake()).executar(PerguntaDTO("oi"))
        assert resposta.graficos == []
        assert resposta.tabelas == []

    def test_resultado_vazio_nao_vira_tabela(self):
        vazio = ResultadoConsulta(series=(), dimensao=Dimensao.UF, metrica=Metrica.VOLUME)
        agente = AgenteFake(RespostaAgente(texto="nada", resultados=(vazio,)))
        assert ResponderPerguntaUseCase(agente).executar(PerguntaDTO("oi")).tabelas == []

    @pytest.mark.parametrize("vazia", ["", "   ", "\n"])
    def test_rejeita_pergunta_vazia(self, vazia):
        with pytest.raises(PerguntaInvalidaError):
            ResponderPerguntaUseCase(AgenteFake()).executar(PerguntaDTO(vazia))

    def test_rejeita_pergunta_longa_demais(self):
        with pytest.raises(PerguntaInvalidaError, match="excede"):
            ResponderPerguntaUseCase(AgenteFake()).executar(PerguntaDTO("a" * 501))
