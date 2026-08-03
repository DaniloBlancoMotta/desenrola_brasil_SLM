"""O agente e testado com um LLM falso: sem chave de API e sem rede."""

import pytest
from langchain_core.messages import AIMessage

from aplicacao.consultar_desenrola import ConsultarDesenrolaUseCase
from infraestrutura.groq_agent import MAX_ITERACOES, AgenteLangChainGroq
from infraestrutura.plotly_renderer import RenderizadorPlotly
from infraestrutura.tools import NOME_TOOL, criar_tool_consulta


class LLMFake:
    """Reproduz o contrato que o agente usa: bind_tools e invoke."""

    def __init__(self, *respostas: AIMessage) -> None:
        self._respostas = list(respostas)
        self.conversas: list[list] = []
        self.ferramentas: list = []

    def bind_tools(self, ferramentas):
        self.ferramentas = ferramentas
        return self

    def invoke(self, mensagens):
        self.conversas.append(list(mensagens))
        if not self._respostas:
            return AIMessage(content="sem mais respostas")
        return self._respostas.pop(0)


def chamada_de_tool(**argumentos) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": NOME_TOOL, "args": argumentos, "id": "chamada-1", "type": "tool_call"}
        ],
    )


@pytest.fixture
def ferramenta(repositorio):
    return criar_tool_consulta(ConsultarDesenrolaUseCase(repositorio, RenderizadorPlotly()))


def montar(ferramenta, repositorio, *respostas) -> tuple[AgenteLangChainGroq, LLMFake]:
    llm = LLMFake(*respostas)
    return AgenteLangChainGroq(llm, ferramenta, repositorio.catalogo()), llm


class TestSystemPrompt:
    def test_inclui_o_catalogo_de_conglomerados(self, ferramenta, repositorio):
        agente, llm = montar(ferramenta, repositorio, AIMessage(content="oi"))
        agente.responder("oi")
        system = llm.conversas[0][0].content
        assert "BB" in system
        assert "dez/2023" in system

    def test_inclui_o_dicionario_de_dados_oficial(self, ferramenta, repositorio):
        agente, llm = montar(ferramenta, repositorio, AIMessage(content="oi"))
        agente.responder("oi")
        system = llm.conversas[0][0].content
        assert "VOLUME_OPERACOES" in system
        assert "AAAAMM" in system

    def test_explica_o_que_cada_modalidade_atende(self, ferramenta, repositorio):
        """Sem isso o agente nao responde quem a Faixa 1 alcancava."""
        agente, llm = montar(ferramenta, repositorio, AIMessage(content="oi"))
        agente.responder("oi")
        system = llm.conversas[0][0].content
        assert "CadUnico" in system
        assert "R$ 5 mil" in system
        assert "R$ 20 mil" in system
        assert "MEI" in system

    def test_alerta_sobre_comparar_modalidades_so_por_volume(self, ferramenta, repositorio):
        """O tique medio difere tanto que volume sozinho engana."""
        agente, llm = montar(ferramenta, repositorio, AIMessage(content="oi"))
        agente.responder("oi")
        assert "numero de operacoes" in llm.conversas[0][0].content

    def test_registra_a_ferramenta_no_modelo(self, ferramenta, repositorio):
        _, llm = montar(ferramenta, repositorio, AIMessage(content="oi"))
        assert [f.name for f in llm.ferramentas] == [NOME_TOOL]


class TestLacoDeFerramentas:
    def test_resposta_direta_dispensa_ferramenta(self, ferramenta, repositorio):
        agente, _ = montar(
            ferramenta, repositorio, AIMessage(content="Esses dados cobrem apenas o Desenrola.")
        )
        resposta = agente.responder("Qual a taxa Selic?")
        assert resposta.texto == "Esses dados cobrem apenas o Desenrola."
        assert resposta.graficos == ()

    def test_captura_o_grafico_do_artefato(self, ferramenta, repositorio):
        """A figura chega a resposta HTTP sem nunca passar pelo modelo."""
        agente, _ = montar(
            ferramenta,
            repositorio,
            chamada_de_tool(agrupar_por="conglomerado"),
            AIMessage(content="O BB lidera."),
        )
        resposta = agente.responder("ranking de bancos")
        assert resposta.texto == "O BB lidera."
        assert len(resposta.graficos) == 1
        assert len(resposta.resultados) == 1

    def test_duas_consultas_acumulam_dois_graficos(self, ferramenta, repositorio):
        """Antes o segundo artefato sobrescrevia o primeiro e um grafico sumia."""
        agente, _ = montar(
            ferramenta,
            repositorio,
            chamada_de_tool(agrupar_por="conglomerado"),
            chamada_de_tool(agrupar_por="uf"),
            AIMessage(content="Seguem as duas visoes."),
        )
        resposta = agente.responder("ranking de bancos e de estados")
        assert len(resposta.graficos) == 2
        assert len(resposta.resultados) == 2

    def test_resultado_da_ferramenta_volta_ao_modelo(self, ferramenta, repositorio):
        agente, llm = montar(
            ferramenta,
            repositorio,
            chamada_de_tool(agrupar_por="conglomerado"),
            AIMessage(content="pronto"),
        )
        agente.responder("ranking")
        segunda_conversa = llm.conversas[1]
        assert "BB" in segunda_conversa[-1].content

    def test_interrompe_apos_o_limite_de_iteracoes(self, ferramenta, repositorio):
        """Sem o teto, um modelo em laco chamaria a ferramenta indefinidamente."""
        repetidas = [chamada_de_tool(agrupar_por="conglomerado") for _ in range(MAX_ITERACOES + 2)]
        agente, llm = montar(ferramenta, repositorio, *repetidas)
        resposta = agente.responder("ranking")
        assert "Nao consegui concluir" in resposta.texto
        assert len(llm.conversas) == MAX_ITERACOES
        assert resposta.graficos, "o que ja foi obtido nao se perde"


class TestConteudoEmBlocos:
    def test_extrai_texto_de_modelos_com_reasoning(self, ferramenta, repositorio):
        """gpt-oss devolve content como lista de blocos, nao string."""
        blocos = AIMessage(
            content=[
                {"type": "reasoning", "reasoning": "pensando..."},
                {"type": "text", "text": "O BB lidera em SP."},
            ]
        )
        agente, _ = montar(ferramenta, repositorio, blocos)
        assert agente.responder("quem lidera?").texto == "O BB lidera em SP."
