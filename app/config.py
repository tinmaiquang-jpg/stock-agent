from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Chi can khi backend = 'api_key'. Backend 'subscription' dung
    # CLAUDE_CODE_OAUTH_TOKEN (Agent SDK doc truc tiep tu bien moi truong).
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-5"

    telegram_bot_token: str
    telegram_owner_id: int

    supabase_url: str
    supabase_key: str

    admin_username: str = "admin"
    admin_password_hash: str
    app_secret_key: str

    fernet_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
