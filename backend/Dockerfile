FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# O venv fica FORA de /app porque /app recebe bind mount do host em
# desenvolvimento, o que esconderia um .venv criado no diretorio do projeto.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Camada de dependencias separada do codigo-fonte: so reconstroi quando
# pyproject.toml ou uv.lock mudam.
COPY pyproject.toml ./
RUN uv sync --no-install-project

COPY . .

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
