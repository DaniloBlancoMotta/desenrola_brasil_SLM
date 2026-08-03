"""Portas: as tres dependencias externas do nucleo, como interfaces.

O dominio define o contrato; a infraestrutura fornece as implementacoes
(dados, LLM e biblioteca de graficos).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from dominio.catalogo import Catalogo, ResumoDaBase
from dominio.consulta import ConsultaDesenrola, ResultadoConsulta
from dominio.visualizacao import EspecificacaoGrafico


class RepositorioDesenrola(Protocol):
    def consultar(self, consulta: ConsultaDesenrola) -> ResultadoConsulta: ...

    def catalogo(self) -> Catalogo: ...

    def resumo(self) -> ResumoDaBase: ...


class RenderizadorGrafico(Protocol):
    def renderizar(self, especificacao: EspecificacaoGrafico) -> dict[str, Any]: ...


@dataclass(frozen=True)
class RespostaAgente:
    texto: str
    graficos: tuple[dict[str, Any], ...] = ()
    """Uma consulta por grafico: o agente pode consultar mais de uma vez."""

    resultados: tuple[ResultadoConsulta, ...] = ()
    """Dados completos, para o frontend tabular sem depender do texto do modelo."""


class AgenteConversacional(Protocol):
    def responder(self, pergunta: str) -> RespostaAgente: ...
