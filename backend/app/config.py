"""Application settings, env-driven (12-factor)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"

    # LLM — provider is swappable via env; default "fake" so the agent core runs
    # fully offline/deterministic in dev and CI with no API key.
    llm_provider: str = "fake"          # fake | gemini | openai | ollama
    llm_model: str = "gemini-2.0-flash"
    llm_temperature: float = 0.0
    gemini_api_key: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"


settings = Settings()
