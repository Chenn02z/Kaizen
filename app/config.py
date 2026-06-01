from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    telegram_token: str
    allowed_user_id: int
    database_url: str
    telegram_webhook_secret: str


settings = Settings()
