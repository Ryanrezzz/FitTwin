"""Application settings, env-driven (12-factor)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"

    # ── API ──
    api_v1_prefix: str = "/api/v1"
    # Comma-separated web origins allowed by CORS (locked to the frontend in prod).
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    # Guards the LLM/agent path against runaway loops.
    agent_recursion_limit: int = 25

    # ── Database (MongoDB / Beanie) ──
    # db_enabled=False lets the API run fully offline (agent core only); auth and
    # profile routes then return 503. Tests disable it and inject in-memory repos.
    db_enabled: bool = True
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "fittwin"
    # Short so a missing/unreachable Mongo fails fast instead of hanging startup.
    mongo_timeout_ms: int = 2000

    # ── Security (JWT + password hashing) ──
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 7

    # LLM — provider is swappable via env; default "fake" so the agent core runs
    # fully offline/deterministic in dev and CI with no API key.
    llm_provider: str = "fake"          # fake | gemini | openai | ollama
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.0
    gemini_api_key: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
