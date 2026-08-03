"""Configuracao por ambiente."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    """llama-3.3-70b-versatile e llama-3.1-8b-instant foram depreciados em jun/2026."""

    csv_path: Path = Path("/data/bacen_data.csv")
    cors_origins: tuple[str, ...] = ("http://localhost:4200", "http://127.0.0.1:4200")
    temperatura: float = 0.0
