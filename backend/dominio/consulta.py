"""Objeto de consulta e resultado agregado.

O resultado e sempre uma colecao de series: uma so para a consulta simples,
varias quando a pergunta compara entidades ("SP contra RJ ao longo do tempo").
"""

from __future__ import annotations

from dataclasses import dataclass

from dominio.conglomerado import Conglomerado
from dominio.dimensao import Dimensao
from dominio.metrica import Metrica
from dominio.periodo import Periodo
from dominio.tipo_desenrola import TipoDesenrola
from dominio.unidade_federacao import UnidadeFederacao


@dataclass(frozen=True)
class ConsultaDesenrola:
    """Um objeto no lugar de oito parametros soltos (Query Object)."""

    agrupar_por: Dimensao
    metrica: Metrica = Metrica.VOLUME
    ufs: tuple[UnidadeFederacao, ...] = ()
    conglomerados: tuple[Conglomerado, ...] = ()
    tipo: TipoDesenrola | None = None
    periodo_inicio: Periodo | None = None
    periodo_fim: Periodo | None = None
    limite: int | None = None

    def __post_init__(self) -> None:
        if self.limite is not None and self.limite < 1:
            raise ValueError(f"Limite deve ser positivo, recebido: {self.limite}")
        if (
            self.periodo_inicio is not None
            and self.periodo_fim is not None
            and self.periodo_inicio > self.periodo_fim
        ):
            raise ValueError(
                f"Periodo inicial {self.periodo_inicio} e posterior ao final {self.periodo_fim}"
            )
        if len(self.ufs) > 1 and len(self.conglomerados) > 1:
            # Duas dimensoes de comparacao ao mesmo tempo dariam um produto
            # cartesiano de series, ilegivel em qualquer grafico.
            raise ValueError(
                "Compare varias UFs ou varios conglomerados, nao os dois ao mesmo tempo."
            )

    @property
    def dimensao_de_comparacao(self) -> Dimensao | None:
        """Qual filtro plural vira uma serie por valor.

        Se a consulta ja agrupa por essa dimensao, a lista e apenas um filtro:
        agrupar por UF com varias UFs continua sendo um ranking, nao uma
        comparacao de series.
        """
        if len(self.ufs) > 1 and self.agrupar_por is not Dimensao.UF:
            return Dimensao.UF
        if len(self.conglomerados) > 1 and self.agrupar_por is not Dimensao.CONGLOMERADO:
            return Dimensao.CONGLOMERADO
        return None

    @property
    def descricao_filtros(self) -> str:
        partes: list[str] = []
        if self.ufs:
            partes.append(" x ".join(uf.nome for uf in self.ufs))
        if self.conglomerados:
            partes.append(" x ".join(c.nome_exibicao for c in self.conglomerados))
        if self.tipo is not None:
            partes.append(self.tipo.descricao)
        if self.periodo_inicio is not None and self.periodo_fim is not None:
            partes.append(f"{self.periodo_inicio} a {self.periodo_fim}")
        elif self.periodo_inicio is not None:
            partes.append(f"a partir de {self.periodo_inicio}")
        elif self.periodo_fim is not None:
            partes.append(f"ate {self.periodo_fim}")
        return ", ".join(partes)


@dataclass(frozen=True)
class LinhaResultado:
    rotulo: str
    valor: float


@dataclass(frozen=True)
class Serie:
    linhas: tuple[LinhaResultado, ...]
    nome: str = ""
    """Vazio na consulta simples; o valor comparado quando ha varias series."""


@dataclass(frozen=True)
class ResultadoConsulta:
    series: tuple[Serie, ...]
    dimensao: Dimensao
    metrica: Metrica
    descricao_filtros: str = ""
    total_de_grupos: int = 0
    """Grupos antes do limite, para a resposta poder avisar que houve corte."""

    @classmethod
    def de_linhas(
        cls,
        linhas: tuple[LinhaResultado, ...],
        dimensao: Dimensao,
        metrica: Metrica,
        descricao_filtros: str = "",
        total_de_grupos: int = 0,
    ) -> ResultadoConsulta:
        return cls(
            series=(Serie(linhas),) if linhas else (),
            dimensao=dimensao,
            metrica=metrica,
            descricao_filtros=descricao_filtros,
            total_de_grupos=total_de_grupos or len(linhas),
        )

    @property
    def linhas(self) -> tuple[LinhaResultado, ...]:
        """Atalho para o caso de serie unica, que e a maioria."""
        return self.series[0].linhas if self.series else ()

    @property
    def vazio(self) -> bool:
        return all(not serie.linhas for serie in self.series)

    @property
    def comparativo(self) -> bool:
        return len(self.series) > 1

    @property
    def maior_serie(self) -> int:
        return max((len(serie.linhas) for serie in self.series), default=0)

    @property
    def total(self) -> float:
        return sum(linha.valor for serie in self.series for linha in serie.linhas)

    @property
    def foi_truncado(self) -> bool:
        return self.total_de_grupos > self.maior_serie
