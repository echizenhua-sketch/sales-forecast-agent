"""Application settings and environment-backed configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the backend service."""

    app_name: str = "产销预测智能工作台"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./data/app.db"
    data_dir: Path = Field(default=Path("data"))
    max_upload_size_mb: int = 50
    session_cookie_name: str = "forecast_agent_session"
    secret_key: str = "dev-secret-key"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    """Return settings from the current process environment."""
    return Settings()
