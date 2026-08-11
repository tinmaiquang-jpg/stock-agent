from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Chi can khi backend = 'api_key'. Backend 'subscription' dung
    # CLAUDE_CODE_OAUTH_TOKEN (Agent SDK doc truc tiep tu bien moi truong).
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-5"

    # Token tu `claude setup-token` (han 1 nam). Backend 'subscription' truyen bien nay
    # vao subprocess cua Agent SDK - xem app/agent/backend_sdk.py:_sdk_env
    claude_code_oauth_token: str = ""

    # Khong bat buoc: web admin deploy rieng (Vercel) khong dung Telegram. Phan chay bot
    # kiem tra lai o app/telegram_bot/bot.py va bao loi ro rang neu thieu.
    telegram_bot_token: str = ""
    telegram_owner_id: int = 0

    supabase_url: str
    supabase_key: str

    # Cookie session chi gui qua HTTPS. Mac dinh True cho an toan; .env local dat false
    # de dang nhap duoc qua http://127.0.0.1
    session_https_only: bool = True

    admin_username: str = "admin"
    admin_password_hash: str
    app_secret_key: str

    fernet_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
