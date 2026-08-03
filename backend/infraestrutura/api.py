"""Fronteira HTTP e composicao das dependencias.

Este e o unico lugar que conhece todas as camadas ao mesmo tempo: monta o grafo
de objetos na subida e o mantem como singleton pelo tempo de vida da aplicacao.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from aplicacao.consultar_desenrola import ConsultarDesenrolaUseCase
from aplicacao.dtos import PerguntaDTO
from aplicacao.responder_pergunta import (
    LIMITE_CARACTERES,
    PerguntaInvalidaError,
    ResponderPerguntaUseCase,
)
from dominio.dicionario_dados import DICIONARIO_COLUNAS, MODALIDADES
from infraestrutura import paleta
from infraestrutura.csv_repository import RepositorioDesenrolaCSV
from infraestrutura.groq_agent import AgenteLangChainGroq
from infraestrutura.plotly_renderer import RenderizadorPlotly
from infraestrutura.settings import Settings
from infraestrutura.tools import criar_tool_consulta

logger = logging.getLogger(__name__)

SEM_CHAVE = (
    "O agente nao esta configurado: defina GROQ_API_KEY no arquivo .env e reinicie a "
    "aplicacao. Obtenha uma chave em https://console.groq.com/keys"
)


class PerguntaRequest(BaseModel):
    pergunta: str = Field(min_length=1, max_length=LIMITE_CARACTERES)


class TabelaResponse(BaseModel):
    titulo: str
    dimensao: str
    metrica: str
    series: list[str]
    linhas: list[dict[str, Any]]


class RespostaResponse(BaseModel):
    resposta: str
    graficos: list[dict[str, Any]] = []
    tabelas: list[TabelaResponse] = []


class SaudeResponse(BaseModel):
    status: str
    registros: int
    periodo: str
    agente_disponivel: bool


class ModalidadeResponse(BaseModel):
    codigo: int
    nome: str
    tese: str
    publico: str
    teto: str
    dividas: str
    negociacao: str
    garantia: str
    base_legal: str
    cor: str
    """A mesma cor que a modalidade recebe nos graficos, para a interface concordar."""


class BaseResponse(BaseModel):
    """Resumo da origem dos dados, para a interface dizer de onde fala."""

    fonte: str
    url: str
    periodo: str
    meses: int
    registros: int
    conglomerados: int
    ufs: int
    modalidades: list[ModalidadeResponse]
    volume_total: float
    operacoes_totais: int
    colunas: dict[str, str]


def _montar_agente(settings: Settings, repositorio: RepositorioDesenrolaCSV):
    """Sem chave a aplicacao ainda sobe: o front funciona e /api/chat responde 503."""
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY ausente; /api/chat respondera 503.")
        return None

    from langchain_groq import ChatGroq

    ferramenta = criar_tool_consulta(
        ConsultarDesenrolaUseCase(repositorio, RenderizadorPlotly())
    )
    llm = ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=settings.temperatura,
    )
    return AgenteLangChainGroq(llm, ferramenta, repositorio.catalogo())


def obter_responder(request: Request) -> ResponderPerguntaUseCase:
    caso_de_uso = getattr(request.app.state, "responder", None)
    if caso_de_uso is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, SEM_CHAVE)
    return caso_de_uso


def criar_aplicacao(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Closure sobre os settings recebidos: o que a fabrica injeta e o que vale."""
        repositorio = RepositorioDesenrolaCSV(settings.csv_path)
        logger.info("CSV carregado de %s", settings.csv_path)

        agente = _montar_agente(settings, repositorio)
        app.state.repositorio = repositorio
        app.state.responder = ResponderPerguntaUseCase(agente) if agente else None
        yield

    app = FastAPI(
        title="Agente Desenrola",
        description="Converse com os dados abertos do programa Desenrola (Banco Central).",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.post("/api/chat", response_model=RespostaResponse)
    def conversar(
        requisicao: PerguntaRequest,
        responder: ResponderPerguntaUseCase = Depends(obter_responder),
    ) -> RespostaResponse:
        try:
            resposta = responder.executar(PerguntaDTO(requisicao.pergunta))
        except PerguntaInvalidaError as erro:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(erro)) from erro
        except Exception as erro:  # falha do provedor de LLM, rede, etc.
            logger.exception("Falha ao responder a pergunta")
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "O modelo nao respondeu. Tente novamente em instantes.",
            ) from erro

        return RespostaResponse(
            resposta=resposta.resposta,
            graficos=resposta.graficos,
            tabelas=[TabelaResponse(**vars(tabela)) for tabela in resposta.tabelas],
        )

    @app.get("/api/base", response_model=BaseResponse)
    def base(request: Request) -> BaseResponse:
        repositorio: RepositorioDesenrolaCSV = request.app.state.repositorio
        resumo = repositorio.resumo()
        return BaseResponse(
            fonte=resumo.fonte,
            url=resumo.url,
            periodo=resumo.periodo,
            meses=resumo.meses,
            registros=resumo.registros,
            conglomerados=resumo.conglomerados,
            ufs=resumo.ufs,
            modalidades=[
                ModalidadeResponse(
                    **vars(modalidade),
                    # A ordem dos slots segue o codigo: e assim que a politica de
                    # visualizacao pinta as barras agrupadas por modalidade.
                    cor=paleta.cor_da_serie(indice),
                )
                for indice, modalidade in enumerate(MODALIDADES)
            ],
            volume_total=resumo.volume_total,
            operacoes_totais=resumo.operacoes_totais,
            colunas=DICIONARIO_COLUNAS,
        )

    @app.get("/api/saude", response_model=SaudeResponse)
    def saude(request: Request) -> SaudeResponse:
        repositorio: RepositorioDesenrolaCSV = request.app.state.repositorio
        catalogo = repositorio.catalogo()
        return SaudeResponse(
            status="ok",
            registros=repositorio.total_de_registros,
            periodo=f"{catalogo.periodo_inicio} a {catalogo.periodo_fim}",
            agente_disponivel=request.app.state.responder is not None,
        )

    return app
