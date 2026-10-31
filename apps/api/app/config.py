from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[3] / ".env", extra="ignore")

    app_env: Literal["development", "staging", "production"] = "development"
    # Temporary guard for internal endpoints until user login exists.
    internal_api_key: SecretStr | None = None

    database_url: str
    migration_database_url: str | None = None
    db_schema: str | None = None
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_connect_timeout: int = 10

    redis_url: str = "redis://localhost:6379/0"

    gemini_api_key: SecretStr
    gemini_model: str
    gemini_timeout_s: float = 30
    gemini_max_retries: int = 3
    gemini_max_concurrency: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
