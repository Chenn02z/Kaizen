from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_async_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return database_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    telegram_token: str
    allowed_user_id: int
    database_url: str
    telegram_webhook_secret: str
    llm_api_key: str
    llm_model: str = "claude-haiku-4-5-20251001"
    embed_api_key: str
    embed_model: str = "text-embedding-3-small"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    public_url: str = ""
    miniapp_secret: str = ""  # protects /me; inject into Mini App HTML at serve time
    scheduler_secret: str = ""  # protects /scheduler/tick
    mem0_api_key: str = ""  # if empty, use local in-memory store
    app_timezone: str = "Asia/Singapore"

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        return normalize_async_database_url(value)


settings = Settings()


def get_app_timezone() -> ZoneInfo:
    return ZoneInfo(settings.app_timezone)
