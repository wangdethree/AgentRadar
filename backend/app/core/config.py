"""应用配置，所有敏感值均从环境变量读取。"""

from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """集中管理运行配置，并兼容根目录与后端目录启动方式。"""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AgentRadar"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: str = "http://localhost:5173"
    database_url: str = "sqlite:///./agentradar.db"
    github_token: str | None = None
    github_api_url: str = "https://api.github.com"
    github_timeout_seconds: float = 15.0
    github_max_retries: int = 2
    github_cache_ttl_seconds: int = 300

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        """把逗号分隔的前端地址转换为 CORS 配置列表。"""
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """缓存配置实例，避免每次请求重复解析环境变量。"""
    return Settings()
