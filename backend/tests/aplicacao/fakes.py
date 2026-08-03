"""Implementacoes falsas das portas: e o que permite testar sem rede nem chave de API."""

from __future__ import annotations

from typing import Any

from dominio.catalogo import Catalogo, ResumoDaBase
from dominio.consulta import ConsultaDesenrola, LinhaResultado, ResultadoConsulta, Serie
from dominio.periodo import Periodo
from dominio.portas import RespostaAgente
from dominio.visualizacao import EspecificacaoGrafico


class RepositorioFake:
    def __init__(
        self,
        linhas: tuple[LinhaResultado, ...] = (),
        total_de_grupos: int = 0,
        series: tuple[Serie, ...] | None = None,
    ) -> None:
        self._series = series if series is not None else ((Serie(linhas),) if linhas else ())
        self._total = total_de_grupos or len(linhas)
        self.consultas: list[ConsultaDesenrola] = []

    def consultar(self, consulta: ConsultaDesenrola) -> ResultadoConsulta:
        self.consultas.append(consulta)
        return ResultadoConsulta(
            series=self._series,
            dimensao=consulta.agrupar_por,
            metrica=consulta.metrica,
            descricao_filtros=consulta.descricao_filtros,
            total_de_grupos=self._total,
        )

    def catalogo(self) -> Catalogo:
        return Catalogo(
            conglomerados=("BB", "BRADESCO"),
            ufs=("RJ", "SP"),
            periodo_inicio=Periodo.de_aaaamm(202309),
            periodo_fim=Periodo.de_aaaamm(202606),
        )

    def resumo(self) -> ResumoDaBase:
        catalogo = self.catalogo()
        return ResumoDaBase(
            periodo_inicio=catalogo.periodo_inicio,
            periodo_fim=catalogo.periodo_fim,
            meses=34,
            registros=10937,
            conglomerados=len(catalogo.conglomerados),
            ufs=len(catalogo.ufs),
            modalidades=("Faixa 1 (pessoas fisicas)",),
            volume_total=1000.0,
            operacoes_totais=10,
        )


class RenderizadorFake:
    def __init__(self) -> None:
        self.chamadas: list[EspecificacaoGrafico] = []

    def renderizar(self, especificacao: EspecificacaoGrafico) -> dict[str, Any]:
        self.chamadas.append(especificacao)
        return {"tipo": especificacao.tipo.value, "titulo": especificacao.titulo}


class AgenteFake:
    def __init__(self, resposta: RespostaAgente | None = None) -> None:
        self.resposta = resposta or RespostaAgente(texto="resposta de teste")
        self.perguntas: list[str] = []

    def responder(self, pergunta: str) -> RespostaAgente:
        self.perguntas.append(pergunta)
        return self.resposta
