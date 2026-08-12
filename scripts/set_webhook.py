"""Dang ky webhook Telegram tro ve URL Vercel (chay 1 lan sau khi deploy).

    python scripts/set_webhook.py https://ten-app.vercel.app

Doc TELEGRAM_BOT_TOKEN va TELEGRAM_WEBHOOK_SECRET tu .env. Muon quay lai che do polling
(chay local/Docker) thi go webhook di:

    python scripts/set_webhook.py --delete
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram import Bot  # noqa: E402

from app.config import get_settings  # noqa: E402


async def main() -> int:
    settings = get_settings()
    if not settings.telegram_bot_token:
        print("Thieu TELEGRAM_BOT_TOKEN trong .env", file=sys.stderr)
        return 1

    bot = Bot(token=settings.telegram_bot_token)
    args = sys.argv[1:]

    if args and args[0] == "--delete":
        await bot.delete_webhook(drop_pending_updates=True)
        print("Da go webhook. Bot quay ve che do polling.")
        return 0

    if not args:
        info = await bot.get_webhook_info()
        print(f"Webhook hien tai: {info.url or '(khong co - dang polling)'}")
        if info.last_error_message:
            print(f"Loi gan nhat: {info.last_error_message}")
        print(f"Update dang cho: {info.pending_update_count}")
        print("\nDat webhook moi: python scripts/set_webhook.py https://ten-app.vercel.app")
        return 0

    if not settings.telegram_webhook_secret:
        print(
            "Thieu TELEGRAM_WEBHOOK_SECRET trong .env.\n"
            "Sinh bang: python -c \"import secrets; print(secrets.token_urlsafe(32))\"",
            file=sys.stderr,
        )
        return 1

    url = args[0].rstrip("/") + "/telegram/webhook"
    await bot.set_webhook(
        url=url,
        secret_token=settings.telegram_webhook_secret,
        drop_pending_updates=True,
    )
    print(f"Da dat webhook: {url}")
    print("Kiem tra bang cach nhan tin cho bot tren Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
