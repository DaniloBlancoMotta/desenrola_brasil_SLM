"""Ponto de entrada do uvicorn."""

import logging

from infraestrutura.api import criar_aplicacao

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = criar_aplicacao()
