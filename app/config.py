from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("*", mode="before")
    @classmethod
    def _strip_whitespace(cls, value):
        """Cat khoang trang thua o moi bien.

        Dan secret vao o Environment Variables cua Vercel rat de kem theo dau xuong dong;
        khi do token dai 109 thay vi 108 va API tu choi voi loi kho hieu. Da mat nhieu vong
        lap vi chuyen nay - xu ly mot lan o day thay vi rai .strip() khap noi.
        """
        return value.strip() if isinstance(value, str) else value

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

    # Chi dung o che do webhook (Vercel). Telegram gui lai chuoi nay trong header
    # X-Telegram-Bot-Api-Secret-Token de chung minh request that su tu Telegram.
    telegram_webhook_secret: str = ""

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
