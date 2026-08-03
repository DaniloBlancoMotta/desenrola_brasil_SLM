"""Caso de uso da fronteira HTTP: recebe a pergunta e devolve o DTO de resposta."""

from __future__ import annotations

from aplicacao.dtos import PerguntaDTO, RespostaDTO
from dominio.portas import AgenteConversacional

LIMITE_CARACTERES = 500


class PerguntaInvalidaError(ValueError):
    pass


class ResponderPerguntaUseCase:
    def __init__(self, agente: AgenteConversacional) -> None:
        self._agente = agente

    def executar(self, entrada: PerguntaDTO) -> RespostaDTO:
        pergunta = entrada.pergunta.strip()
        if not pergunta:
            raise PerguntaInvalidaError("A pergunta esta vazia.")
        if len(pergunta) > LIMITE_CARACTERES:
            raise PerguntaInvalidaError(
                f"A pergunta excede {LIMITE_CARACTERES} caracteres."
            )

        resposta = self._agente.responder(pergunta)
        return RespostaDTO.de_agente(resposta.texto, resposta.graficos, resposta.resultados)
