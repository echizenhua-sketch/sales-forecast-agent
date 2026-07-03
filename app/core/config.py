"""
应用配置
"""

from pathlib import Path
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """运行时配置"""

    # 应用配置
    app_name: str = "产销预测智能工作台"
    api_prefix: str = "/api"

    # 数据库配置
    database_url: str = Field(
        default="mysql+pymysql://root:password@10.10.9.104:11123/supply_demand_forecast?charset=utf8mb4",
        description="数据库连接 URL"
    )

    # 文件上传配置
    data_dir: Path = Field(default=Path("data"))
    upload_dir: Path = Field(default=Path("data/uploads"))
    max_upload_size_mb: int = 50

    # 会话配置
    secret_key: str = "change-me-in-production"
    session_cookie_name: str = "forecast_agent_session"
    session_expire_hours: int = 24

    # 日志配置
    log_level: str = "INFO"
    log_dir: Path = Field(default=Path("logs"))

    # AI 模型配置
    ai_api_base: str = ""
    ai_api_key: str = ""
    ai_model: str = "MiniMax-M3"
    anthropic_base_url: str = ""
    anthropic_auth_token: str = ""

    # 长期记忆配置
    memory_enabled: bool = False
    memory_backend: str = "jsonl"
    memory_dir: Path = Field(default=Path(".runtime/mem0"))
    memory_search_limit: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        if self.memory_enabled:
            self.memory_dir.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
