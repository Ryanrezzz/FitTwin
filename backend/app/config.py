"""Application settings, env-driven (12-factor)."""
from __future__ import annotations

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-to-a-long-random-string"


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
    # ── Google Sign-In ──
    # The OAuth 2.0 Web client id from Google Cloud Console. Empty disables the
    # feature cleanly (the endpoint returns 503) rather than half-enabling it.
    # It is NOT a secret — it ships to the browser — so it has no prod guard.
    google_client_id: str = ""

    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    # Auth rate limiting. Disabled in the test suite (which logs in constantly);
    # must stay on everywhere else.
    rate_limit_enabled: bool = True
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 7

    # LLM — provider is swappable via env; default "fake" so the agent core runs
    # fully offline/deterministic in dev and CI with no API key.
    llm_provider: str = "fake"          # fake | gemini | openai | ollama
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.0
    # Reproducibility. Some models (gpt-5.5, gpt-5.6-*) reject any temperature but
    # the default 1, so temperature alone can't pin them down — LangChain silently
    # drops it. `seed` is what actually makes those models repeatable: same profile
    # in => same plan out. Set to None for deliberate variety.
    llm_seed: int | None = 42
    gemini_api_key: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # Dashboard/CI env fields routinely pick up a trailing newline from a
    # paste — a textarea, or `echo` into a secret store. A client id ending in
    # "\n" is a DIFFERENT string to Google and fails as an unknown client, with
    # an error that points nowhere near the cause. Strip on the way in.
    @field_validator(
        "google_client_id", "openai_api_key", "gemini_api_key",
        "jwt_secret", "mongo_uri", "cors_origins", "llm_model", "llm_provider",
        mode="before",
    )
    @classmethod
    def _strip_whitespace(cls, v: object) -> object:
        return v.strip() if isinstance(v, str) else v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.app_env.lower() in ("prod", "production", "staging")

    @model_validator(mode="after")
    def _refuse_insecure_prod(self) -> Settings:
        """Fail fast rather than boot a live app with forgeable sessions.

        The default JWT secret is public (it ships in .env.example), so anyone
        could mint an admin token against a deployment that kept it. In dev we
        allow it for convenience; outside dev, refusing to start is the only
        safe behaviour. A wildcard CORS origin with credentials is refused for
        the same reason.
        """
        if not self.is_prod:
            return self
        if self.jwt_secret == DEFAULT_JWT_SECRET or len(self.jwt_secret) < 32:
            raise ValueError(
                "JWT_SECRET is unset, default, or too short. Set a random 32+ char "
                f"secret before running with APP_ENV={self.app_env}."
            )
        if "*" in self.cors_origin_list:
            raise ValueError("CORS_ORIGINS must not be '*' when credentials are allowed.")
        return self


settings = Settings()
