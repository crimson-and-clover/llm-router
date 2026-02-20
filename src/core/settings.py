from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "llm-router"
    env: str = "dev"  # dev / prod
    debug: bool = False

    # ========== Moonshot ==========
    moonshot_base_url: str | None
    moonshot_api_key: str | None

    # ========== DeepSeek ==========
    deepseek_base_url: str | None
    deepseek_api_key: str | None

    # ========== Zai ==========
    zai_base_url: str | None
    zai_api_key: str | None

    # ========== JWT / Auth ==========
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 2  # 2 小时（减少重放攻击窗口）

    # ========== Logging ==========
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_async: bool = True  # 使用队列异步日志，提高性能
    log_format: str = "text"  # text 或 json
    log_access: bool = False  # 是否启用 uvicorn access 日志

    internal_secret: str = "sk-xxxxxx"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # env 里多余的变量不报错
    )


@lru_cache
def get_settings() -> Settings:
    """
    用 lru_cache 确保整个进程只有一个 Settings 实例
    """
    return Settings()
