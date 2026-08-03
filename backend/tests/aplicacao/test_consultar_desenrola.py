from aplicacao.consultar_desenrola import LINHAS_NO_RESUMO, ConsultarDesenrolaUseCase
from dominio.consulta import ConsultaDesenrola, LinhaResultado, Serie
from dominio.dimensao import Dimensao
from tests.aplicacao.fakes import RenderizadorFake, RepositorioFake


def caso_de_uso(linhas=(), total=0, series=None):
    repositorio = RepositorioFake(linhas, total, series)
    renderizador = RenderizadorFake()
    return ConsultarDesenrolaUseCase(repositorio, renderizador), repositorio, renderizador


def linhas_de(quantidade: int) -> tuple[LinhaResultado, ...]:
    return tuple(LinhaResultado(f"B{i}", float(quantidade - i)) for i in range(quantidade))


class TestOrquestracao:
    def test_gera_grafico_quando_ha_varias_linhas(self):
        uso, _, renderizador = caso_de_uso(
            (LinhaResultado("BB", 100.0), LinhaResultado("ITAU", 50.0))
        )
        executada = uso.executar(ConsultaDesenrola(agrupar_por=Dimensao.CONGLOMERADO))
        assert executada.grafico is not None
        assert len(renderizador.chamadas) == 1

    def test_nao_gera_grafico_para_resposta_de_um_numero(self):
        """A politica de dominio evita o grafico inutil de uma barra so."""
        uso, _, renderizador = caso_de_uso((LinhaResultado("BB", 100.0),))
        executada = uso.executar(ConsultaDesenrola(agrupar_por=Dimensao.CONGLOMERADO))
        assert executada.grafico is None
        assert renderizador.chamadas == []

    def test_repassa_a_consulta_ao_repositorio(self):
        uso, repositorio, _ = caso_de_uso()
        consulta = ConsultaDesenrola(agrupar_por=Dimensao.UF, limite=5)
        uso.executar(consulta)
        assert repositorio.consultas == [consulta]


class TestResumoTextual:
    def test_lista_os_itens_formatados(self):
        uso, _, _ = caso_de_uso((LinhaResultado("BB", 1418395.99),))
        resumo = uso.executar(ConsultaDesenrola(agrupar_por=Dimensao.CONGLOMERADO)).resumo_textual()
        assert "1. BB: R$ 1.418.395,99" in resumo

    def test_avisa_quando_a_consulta_foi_limitada(self):
        uso, _, _ = caso_de_uso(linhas_de(5), total=64)
        resumo = uso.executar(ConsultaDesenrola(agrupar_por=Dimensao.CONGLOMERADO)).resumo_textual()
        assert "5 de 64 grupos" in resumo

    def test_as_27_ufs_cabem_inteiras_no_resumo(self):
        """O corte antigo em 20 escondia 7 estados de uma pergunta por 'cada estado'."""
        uso, _, _ = caso_de_uso(linhas_de(27))
        resumo = uso.executar(ConsultaDesenrola(agrupar_por=Dimensao.UF)).resumo_textual()
        assert "27. " in resumo
        assert "ATENCAO" not in resumo

    def test_os_34_meses_cabem_inteiros_no_resumo(self):
        uso, _, _ = caso_de_uso(linhas_de(34))
        resumo = uso.executar(ConsultaDesenrola(agrupar_por=Dimensao.PERIODO)).resumo_textual()
        assert "34. " in resumo

    def test_corte_do_resumo_e_anunciado_em_voz_alta(self):
        """Truncar em silencio fez o modelo afirmar que os dados terminavam ali."""
        uso, _, _ = caso_de_uso(linhas_de(64))
        resumo = uso.executar(ConsultaDesenrola(agrupar_por=Dimensao.CONGLOMERADO)).resumo_textual()
        assert f"listei apenas {LINHAS_NO_RESUMO} de 64" in resumo
        assert "NAO afirme que esta lista e completa" in resumo

    def test_avisa_quando_o_grafico_mostra_menos_que_os_dados(self):
        """As 27 UFs cabem no texto, mas o grafico so desenha 15 -- o modelo precisa saber."""
        uso, _, _ = caso_de_uso(linhas_de(27))
        resumo = uso.executar(ConsultaDesenrola(agrupar_por=Dimensao.UF)).resumo_textual()
        assert "grafico mostra os 15 maiores" in resumo

    def test_informa_ao_llm_que_o_grafico_ja_existe(self):
        uso, _, _ = caso_de_uso((LinhaResultado("BB", 100.0), LinhaResultado("ITAU", 50.0)))
        resumo = uso.executar(ConsultaDesenrola(agrupar_por=Dimensao.CONGLOMERADO)).resumo_textual()
        assert "grafico" in resumo.lower()

    def test_pede_ao_llm_para_nao_reproduzir_a_tabela(self):
        uso, _, _ = caso_de_uso(linhas_de(10))
        resumo = uso.executar(ConsultaDesenrola(agrupar_por=Dimensao.UF)).resumo_textual()
        assert "nao a reproduza" in resumo.lower()

    def test_resultado_vazio_diz_isso_claramente(self):
        uso, _, _ = caso_de_uso()
        resumo = uso.executar(ConsultaDesenrola(agrupar_por=Dimensao.UF)).resumo_textual()
        assert "Nenhum registro" in resumo


class TestResumoComparativo:
    def test_identifica_cada_serie_pelo_nome(self):
        series = (
            Serie((LinhaResultado("jan/2024", 10.0),), "SP"),
            Serie((LinhaResultado("jan/2024", 4.0),), "RJ"),
        )
        uso, _, _ = caso_de_uso(series=series, total=1)
        resumo = uso.executar(ConsultaDesenrola(agrupar_por=Dimensao.PERIODO)).resumo_textual()
        assert "SP:" in resumo
        assert "RJ:" in resumo
