from pydantic_settings import BaseSettings, SettingsConfigDict


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
    mem0_api_key: str = ""  # if empty, use local in-memory store


settings = Settings()
