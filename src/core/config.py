"""Application settings and environment-backed configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the backend service."""

    app_name: str = "产销预测智能工作台"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./data/app.db"
    redis_url: str = "redis://localhost:6379/0"
    max_upload_size_mb: int = 20
    session_cookie_name: str = "forecast_agent_session"
    secret_key: str = "dev-secret-key"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
