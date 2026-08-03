"""Valida que o container tem as dependencias que o projeto declara."""


def test_dependencias_principais_importam():
    import fastapi  # noqa: F401
    import langchain_groq  # noqa: F401
    import pandas  # noqa: F401
    import plotly  # noqa: F401
