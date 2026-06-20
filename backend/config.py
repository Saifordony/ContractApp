"""Environment-driven application settings (pydantic-settings).

Every tunable — Mongo, auth lifetimes, and the entire Ollama configuration — is
read from the environment so a stronger model or a different deployment can be
swapped in without code changes.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "Contract Analysis Platform"
    api_prefix: str = "/api"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- MongoDB ---
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "contract_analysis"

    # --- Auth ---
    secret_key: str = "dev-secret-key-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    password_reset_expire_minutes: int = 30
    # Login rate limit: max failed attempts per key within the window.
    login_rate_limit_max: int = 5
    login_rate_limit_window_seconds: int = 300
    # When true (dev/no mail infra), password-reset tokens are returned in the API
    # response so reset can be completed without an email provider.
    expose_reset_token: bool = True

    # --- Ollama (local LLM, OpenAI-compatible) ---
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.1:8b"
    ollama_temperature: float = 0.1
    ollama_num_ctx: int = 8192
    ollama_timeout: int = 120
    ollama_api_key: str = "ollama"  # placeholder; Ollama ignores it

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
