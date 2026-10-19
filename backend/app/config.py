"""Application settings loaded from environment variables (never hard-code secrets)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MAHSUDo-guide API"
    environment: str = "development"
    debug: bool = False

    # Database: SQLite by default for local development.
    # Set DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db for production.
    database_url: str = f"sqlite:///{BASE_DIR / 'mahsud.db'}"

    # CORS
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Auth / secrets
    secret_key: str = "dev-only-change-me"
    access_token_expire_minutes: int = 60 * 8
    admin_seed_email: str = "admin@example.com"
    admin_seed_password: str = "change-me-in-production"

    # AI providers. "none" keeps the app usable with retrieval-grounded answers only.
    llm_provider: str = "none"  # none | openai | ollama
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    ollama_base_url: str = "http://localhost:11434"

    embedding_provider: str = "local"  # local | openai
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 384

    # Ingestion / politeness
    user_agent: str = "MAHSUDo-guide research bot (+https://github.com/; educational project)"
    fetch_timeout_seconds: float = 30.0
    min_request_interval_seconds: float = 1.0

    # Rate limiting (per client, in-memory)
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
