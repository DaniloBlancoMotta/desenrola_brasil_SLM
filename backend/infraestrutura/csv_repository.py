"""Adaptador de dados: le o CSV do Banco Central com pandas.

O DataFrame e carregado uma unica vez na subida e mantido em memoria -- sao
~11 mil linhas. A normalizacao de conglomerado acontece aqui, na fronteira:
o dominio nunca ve o valor cru do CSV.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from dominio.catalogo import Catalogo, ResumoDaBase
from dominio.conglomerado import Conglomerado
from dominio.consulta import ConsultaDesenrola, LinhaResultado, ResultadoConsulta, Serie
from dominio.dimensao import Dimensao
from dominio.periodo import Periodo
from dominio.tipo_desenrola import TipoDesenrola

COL_DATA = "DATA_BASE"
COL_TIPO = "TIPO_DESENROLA"
COL_UF = "UNIDADE_FEDERACAO"
COL_NOME = "NOME_CONGLOMERADO_FINANCEIRO"
COL_CANONICO = "_conglomerado_canonico"
COL_EXIBICAO = "_conglomerado_exibicao"

_COLUNAS_OBRIGATORIAS = frozenset(
    {COL_DATA, COL_TIPO, COL_UF, COL_NOME, "NUMERO_OPERACOES", "VOLUME_OPERACOES"}
)


class RepositorioDesenrolaCSV:
    def __init__(self, caminho: Path | str) -> None:
        self._dados = self._carregar(Path(caminho))
        self._catalogo = self._montar_catalogo()

    @staticmethod
    def _carregar(caminho: Path) -> pd.DataFrame:
        if not caminho.exists():
            raise FileNotFoundError(f"CSV do Desenrola nao encontrado em {caminho}")

        dados = pd.read_csv(
            caminho,
            sep=";",
            decimal=",",
            encoding="utf-8",
            dtype={COL_UF: str, COL_NOME: str},
        )

        faltando = _COLUNAS_OBRIGATORIAS - set(dados.columns)
        if faltando:
            raise ValueError(f"CSV sem as colunas esperadas: {sorted(faltando)}")

        # Canoniza uma vez por nome distinto (76), nao por linha (~11 mil).
        por_bruto = {bruto: Conglomerado.de_bruto(bruto) for bruto in dados[COL_NOME].unique()}
        dados[COL_CANONICO] = dados[COL_NOME].map(lambda b: por_bruto[b].nome_canonico)
        dados[COL_EXIBICAO] = dados[COL_NOME].map(lambda b: por_bruto[b].nome_exibicao)
        return dados

    def _montar_catalogo(self) -> Catalogo:
        # Ordenado por volume: o corte no system prompt preserva os relevantes.
        por_volume = (
            self._dados.groupby(COL_EXIBICAO)["VOLUME_OPERACOES"].sum().sort_values(ascending=False)
        )
        return Catalogo(
            conglomerados=tuple(por_volume.index),
            ufs=tuple(sorted(self._dados[COL_UF].unique())),
            periodo_inicio=Periodo.de_aaaamm(int(self._dados[COL_DATA].min())),
            periodo_fim=Periodo.de_aaaamm(int(self._dados[COL_DATA].max())),
        )

    def catalogo(self) -> Catalogo:
        return self._catalogo

    def resumo(self) -> ResumoDaBase:
        inicio, fim = self._catalogo.periodo_inicio, self._catalogo.periodo_fim
        return ResumoDaBase(
            periodo_inicio=inicio,
            periodo_fim=fim,
            meses=int(self._dados[COL_DATA].nunique()),
            registros=len(self._dados),
            conglomerados=len(self._catalogo.conglomerados),
            ufs=len(self._catalogo.ufs),
            modalidades=tuple(
                TipoDesenrola.de_codigo(int(codigo)).descricao
                for codigo in sorted(self._dados[COL_TIPO].unique())
            ),
            volume_total=float(self._dados["VOLUME_OPERACOES"].sum()),
            operacoes_totais=int(self._dados["NUMERO_OPERACOES"].sum()),
        )

    @property
    def total_de_registros(self) -> int:
        return len(self._dados)

    def consultar(self, consulta: ConsultaDesenrola) -> ResultadoConsulta:
        filtrado = self._filtrar(consulta)
        vazio = ResultadoConsulta(
            series=(),
            dimensao=consulta.agrupar_por,
            metrica=consulta.metrica,
            descricao_filtros=consulta.descricao_filtros,
            total_de_grupos=0,
        )
        if filtrado.empty:
            return vazio

        comparacao = consulta.dimensao_de_comparacao
        if comparacao is None:
            linhas, total = self._agregar(filtrado, consulta)
            return ResultadoConsulta.de_linhas(
                linhas=linhas,
                dimensao=consulta.agrupar_por,
                metrica=consulta.metrica,
                descricao_filtros=consulta.descricao_filtros,
                total_de_grupos=total,
            )

        series, total = self._agregar_por_serie(filtrado, consulta, comparacao)
        if not series:
            return vazio
        return ResultadoConsulta(
            series=series,
            dimensao=consulta.agrupar_por,
            metrica=consulta.metrica,
            descricao_filtros=consulta.descricao_filtros,
            total_de_grupos=total,
        )

    def _agregar(
        self, dados: pd.DataFrame, consulta: ConsultaDesenrola
    ) -> tuple[tuple[LinhaResultado, ...], int]:
        agregado = dados.groupby(self._coluna_de(consulta.agrupar_por))[
            consulta.metrica.coluna
        ].sum()

        if consulta.agrupar_por.ordena_por_valor:
            agregado = agregado.sort_values(ascending=False)
        else:
            agregado = agregado.sort_index()

        total_de_grupos = len(agregado)
        if consulta.limite is not None:
            agregado = agregado.head(consulta.limite)

        rotular = self._rotulador(consulta.agrupar_por)
        linhas = tuple(
            LinhaResultado(rotulo=rotular(chave), valor=float(valor))
            for chave, valor in agregado.items()
        )
        return linhas, total_de_grupos

    def _agregar_por_serie(
        self, dados: pd.DataFrame, consulta: ConsultaDesenrola, comparacao: Dimensao
    ) -> tuple[tuple[Serie, ...], int]:
        """Uma serie por valor do filtro plural, preservando a ordem pedida."""
        coluna = self._coluna_de(comparacao)
        if comparacao is Dimensao.UF:
            nomes = [uf.sigla for uf in consulta.ufs]
        else:
            nomes = [c.nome_canonico for c in consulta.conglomerados]
            coluna = COL_CANONICO

        series: list[Serie] = []
        total = 0
        for nome in nomes:
            recorte = dados[dados[coluna] == nome]
            if recorte.empty:
                continue
            linhas, grupos = self._agregar(recorte, consulta)
            total = max(total, grupos)
            series.append(Serie(linhas=linhas, nome=self._exibir(recorte, comparacao, nome)))
        return tuple(series), total

    @staticmethod
    def _exibir(recorte: pd.DataFrame, comparacao: Dimensao, nome: str) -> str:
        if comparacao is Dimensao.CONGLOMERADO:
            return str(recorte[COL_EXIBICAO].iloc[0])
        return nome

    def _filtrar(self, consulta: ConsultaDesenrola) -> pd.DataFrame:
        dados = self._dados
        if consulta.ufs:
            dados = dados[dados[COL_UF].isin([uf.sigla for uf in consulta.ufs])]
        if consulta.conglomerados:
            dados = dados[
                dados[COL_CANONICO].isin([c.nome_canonico for c in consulta.conglomerados])
            ]
        if consulta.tipo is not None:
            dados = dados[dados[COL_TIPO] == consulta.tipo.value]
        if consulta.periodo_inicio is not None:
            dados = dados[dados[COL_DATA] >= consulta.periodo_inicio.aaaamm]
        if consulta.periodo_fim is not None:
            dados = dados[dados[COL_DATA] <= consulta.periodo_fim.aaaamm]
        return dados

    @staticmethod
    def _coluna_de(dimensao: Dimensao) -> str:
        return {
            Dimensao.CONGLOMERADO: COL_EXIBICAO,
            Dimensao.UF: COL_UF,
            Dimensao.PERIODO: COL_DATA,
            Dimensao.TIPO: COL_TIPO,
        }[dimensao]

    @staticmethod
    def _rotulador(dimensao: Dimensao):
        if dimensao is Dimensao.PERIODO:
            return lambda chave: str(Periodo.de_aaaamm(int(chave)))
        if dimensao is Dimensao.TIPO:
            return lambda chave: TipoDesenrola.de_codigo(int(chave)).descricao
        return str
