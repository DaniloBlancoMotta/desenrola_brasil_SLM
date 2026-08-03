"""Caso de uso central: consulta os dados e ja decide a visualizacao.

Orquestra repositorio -> politica -> renderizador. A ferramenta exposta ao LLM
e um adaptador fino sobre este caso de uso, para que a orquestracao fique na
aplicacao e nao na infraestrutura.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dominio.consulta import ConsultaDesenrola, ResultadoConsulta, Serie
from dominio.portas import RenderizadorGrafico, RepositorioDesenrola
from dominio.visualizacao import EspecificacaoGrafico, PoliticaVisualizacao

LINHAS_NO_RESUMO = 40
"""Cabe as 27 UFs e os 34 meses inteiros; corta apenas os 64 conglomerados."""


@dataclass(frozen=True)
class ConsultaExecutada:
    resultado: ResultadoConsulta
    grafico: dict[str, Any] | None
    especificacao: EspecificacaoGrafico | None = None

    def resumo_textual(self) -> str:
        """Texto compacto devolvido ao LLM -- a figura viaja como artefato."""
        if self.resultado.vazio:
            return "Nenhum registro encontrado para esses filtros."

        cabecalho = f"{self.resultado.metrica.rotulo} por {self.resultado.dimensao.rotulo.lower()}"
        if self.resultado.descricao_filtros:
            cabecalho += f" ({self.resultado.descricao_filtros})"

        corpo = "\n\n".join(self._bloco(serie) for serie in self.resultado.series)
        return f"{cabecalho}:\n{corpo}{self._rodape()}"

    def _bloco(self, serie: Serie) -> str:
        visiveis = serie.linhas[:LINHAS_NO_RESUMO]
        itens = "\n".join(
            f"{posicao}. {linha.rotulo}: {self.resultado.metrica.formatar(linha.valor)}"
            for posicao, linha in enumerate(visiveis, start=1)
        )
        return f"{serie.nome}:\n{itens}" if serie.nome else itens

    def _rodape(self) -> str:
        avisos: list[str] = []

        # O corte do resumo precisa ser anunciado, senao o modelo apresenta uma
        # lista parcial como se fosse completa -- e chega a afirmar que os dados
        # terminam onde apenas o resumo terminou.
        mostradas = min(self.resultado.maior_serie, LINHAS_NO_RESUMO)
        if mostradas < self.resultado.maior_serie:
            avisos.append(
                f"ATENCAO: listei apenas {mostradas} de {self.resultado.maior_serie} itens por "
                f"serie. NAO afirme que esta lista e completa nem que os dados terminam aqui."
            )
        elif self.resultado.foi_truncado:
            avisos.append(
                f"(mostrando {self.resultado.maior_serie} de "
                f"{self.resultado.total_de_grupos} grupos)"
            )

        if self.especificacao is not None:
            exibidas = self.especificacao.categorias_exibidas
            if exibidas < self.resultado.maior_serie:
                avisos.append(
                    f"O grafico mostra os {exibidas} maiores, nao todos os "
                    f"{self.resultado.maior_serie}."
                )
            else:
                avisos.append("Um grafico ja foi gerado e sera exibido ao usuario.")
            avisos.append("A tabela completa aparece na tela; nao a reproduza na resposta.")

        return "\n" + "\n".join(avisos) if avisos else ""


class ConsultarDesenrolaUseCase:
    def __init__(
        self,
        repositorio: RepositorioDesenrola,
        renderizador: RenderizadorGrafico,
        politica: PoliticaVisualizacao | None = None,
    ) -> None:
        self._repositorio = repositorio
        self._renderizador = renderizador
        self._politica = politica or PoliticaVisualizacao()

    def executar(self, consulta: ConsultaDesenrola) -> ConsultaExecutada:
        resultado = self._repositorio.consultar(consulta)
        especificacao = self._politica.decidir(resultado)
        grafico = self._renderizador.renderizar(especificacao) if especificacao else None
        return ConsultaExecutada(
            resultado=resultado, grafico=grafico, especificacao=especificacao
        )
