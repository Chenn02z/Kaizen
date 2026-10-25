from typing import Any
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


def _base_url(database_url: str) -> URL:
    # Accept the plain libpq URL Supabase hands out, with or without a driver suffix.
    url = make_url(database_url.replace("postgres://", "postgresql://", 1))
    return url.set(drivername="postgresql")


def async_engine_args(database_url: str) -> tuple[URL, dict[str, Any]]:
    """asyncpg rejects libpq's `sslmode` query param, so move it into connect_args."""
    url = _base_url(database_url)
    sslmode = url.query.get("sslmode")
    url = url.difference_update_query(["sslmode"]).set(drivername="postgresql+asyncpg")
    return url, ({"ssl": sslmode} if sslmode else {})


def sync_database_url(database_url: str) -> str:
    """libpq-style URL for Alembic (psycopg2) and Mem0's pgvector store."""
    return _base_url(database_url).render_as_string(hide_password=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True
    )

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
    public_url: str = ""  # HTTPS origin; when set, the webhook is registered on startup
    scheduler_secret: str = ""  # protects /scheduler/tick
    mem0_api_key: str = ""  # if empty, self-host Mem0 on the app's pgvector database
    app_timezone: str = "Asia/Singapore"


settings = Settings()


def get_app_timezone() -> ZoneInfo:
    return ZoneInfo(settings.app_timezone)
