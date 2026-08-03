"""A unica ferramenta exposta ao LLM.

Adaptador fino: traduz os argumentos do modelo em ConsultaDesenrola e delega ao
caso de uso. Nao ha execucao de codigo arbitrario -- cada parametro e validado
contra um enum fechado, e erro de argumento volta ao modelo como texto legivel
para ele se corrigir na proxima iteracao.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from aplicacao.consultar_desenrola import ConsultarDesenrolaUseCase
from dominio.conglomerado import Conglomerado
from dominio.consulta import ConsultaDesenrola
from dominio.dimensao import Dimensao
from dominio.metrica import Metrica
from dominio.periodo import Periodo
from dominio.tipo_desenrola import TipoDesenrola
from dominio.unidade_federacao import UnidadeFederacao

NOME_TOOL = "consultar_desenrola"


class ArgumentosConsulta(BaseModel):
    agrupar_por: Literal["conglomerado", "uf", "periodo", "tipo"] = Field(
        description=(
            "Eixo do agrupamento. Use 'conglomerado' para ranking de bancos, 'uf' para "
            "comparar estados, 'periodo' para evolucao mes a mes, 'tipo' para comparar "
            "as modalidades do programa."
        )
    )
    metrica: Literal["volume", "numero_operacoes"] = Field(
        default="volume",
        description="'volume' soma os valores em reais; 'numero_operacoes' conta as operacoes.",
    )
    ufs: list[str] | None = Field(
        default=None,
        description=(
            "Siglas de UF, ex.: ['SP']. Com duas ou mais e agrupar_por='periodo', devolve "
            "uma serie por estado em um unico grafico comparativo -- prefira isso a fazer "
            "varias chamadas."
        ),
    )
    conglomerados: list[str] | None = Field(
        default=None,
        description=(
            "Nomes de conglomerado como constam no catalogo, ex.: ['BB']. Com dois ou mais "
            "e agrupar_por='periodo', gera um grafico comparativo entre eles."
        ),
    )
    tipo: Literal[1, 2, 3] | None = Field(
        default=None,
        description="1 e 2 sao as faixas do Desenrola pessoas fisicas; 3 e Pequenos Negocios.",
    )
    periodo_inicio: int | None = Field(
        default=None, description="Mes inicial no formato AAAAMM, ex.: 202401."
    )
    periodo_fim: int | None = Field(
        default=None, description="Mes final no formato AAAAMM, ex.: 202412."
    )
    limite: int | None = Field(
        default=None,
        description=(
            "Quantidade maxima de grupos, para perguntas do tipo 'top N'. Deixe vazio "
            "quando o usuario pedir todos."
        ),
    )


def _para_consulta(argumentos: ArgumentosConsulta) -> ConsultaDesenrola:
    return ConsultaDesenrola(
        agrupar_por=Dimensao(argumentos.agrupar_por),
        metrica=Metrica(argumentos.metrica),
        ufs=tuple(UnidadeFederacao.de_texto(uf) for uf in argumentos.ufs or ()),
        conglomerados=tuple(
            Conglomerado.de_bruto(nome) for nome in argumentos.conglomerados or ()
        ),
        tipo=TipoDesenrola.de_codigo(argumentos.tipo) if argumentos.tipo else None,
        periodo_inicio=(
            Periodo.de_aaaamm(argumentos.periodo_inicio) if argumentos.periodo_inicio else None
        ),
        periodo_fim=Periodo.de_aaaamm(argumentos.periodo_fim) if argumentos.periodo_fim else None,
        limite=argumentos.limite,
    )


def criar_tool_consulta(caso_de_uso: ConsultarDesenrolaUseCase) -> BaseTool:
    @tool(NOME_TOOL, args_schema=ArgumentosConsulta, response_format="content_and_artifact")
    def consultar_desenrola(**kwargs: Any) -> tuple[str, dict[str, Any]]:
        """Consulta os dados do Desenrola e, quando faz sentido, gera o grafico.

        Devolve os numeros agregados ja formatados. O grafico e decidido
        automaticamente pela forma do resultado; nao ha parametro para pedi-lo.
        Para comparar estados ou bancos, passe varios valores em ufs ou
        conglomerados numa unica chamada.
        """
        try:
            consulta = _para_consulta(ArgumentosConsulta(**kwargs))
        except ValueError as erro:
            # Texto de erro volta ao modelo, que tenta de novo com outro argumento.
            return f"Argumento invalido: {erro}", {}

        executada = caso_de_uso.executar(consulta)
        artefato = {
            "grafico": executada.grafico,
            "resultado": executada.resultado,
        }
        return executada.resumo_textual(), artefato

    return consultar_desenrola
