from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[4] / ".env", extra="ignore")

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

    # Login accounts (JSON file) and the token signing key. Must stay out of Git.
    auth_data_dir: Path = Path(__file__).resolve().parents[4] / "data" / "auth"

    upload_dir: Path = Path(__file__).resolve().parents[4] / "data" / "uploads"

    meko_api_key: SecretStr | None = None
    meko_mcp_url: str = "https://mcp.mekodata.ai/mcp"
    # Development only. Never set this where real client data is stored.
    meko_shared_datapack_id: str | None = None

    fal_key: SecretStr | None = None
    fal_image_model: str = "fal-ai/flux-2"
    fal_video_model: str = "blackforestlabs/flux-3-max/text-to-video"

    # Verified live on 1 November 2026: both return real media on this key's project.
    gemini_image_model: str = "gemini-3.1-flash-lite-image"
    gemini_video_model: str = "gemini-omni-1.1-flash"
    gemini_media_timeout_s: float = 180

    # Daily per-agency caps on paid media generation.
    media_daily_image_limit: int = 100
    media_daily_video_limit: int = 10

    # Counts every AI workflow run per agency, as a cost guard until usage billing exists.
    ai_daily_run_limit: int = 200

    redis_url: str = "redis://localhost:6379/0"

    gemini_api_key: SecretStr
    gemini_model: str
    gemini_timeout_s: float = 30
    gemini_max_retries: int = 3
    gemini_max_concurrency: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
