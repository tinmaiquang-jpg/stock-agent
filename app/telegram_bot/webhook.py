"""Telegram o che do webhook - danh cho Vercel (serverless khong chay polling duoc).

Dung chung toan bo handler voi che do polling trong bot.py, chi khac cach nhan update:
polling thi bot tu hoi Telegram, webhook thi Telegram POST vao day.
"""

import hmac
import logging

from fastapi import APIRouter, Header, Request, Response
from telegram import Update

from app.config import get_settings
from app.db import repository
from app.telegram_bot.bot import build_application

logger = logging.getLogger(__name__)

router = APIRouter()

_application = None


async def _get_application():
    """Khoi tao 1 lan roi dung lai cho cac request sau trong cung container (Vercel giu
    container am mot luc), tranh chi phi khoi tao moi request."""
    global _application
    if _application is None:
        app = build_application()
        await app.initialize()
        _application = app
    return _application


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    settings = get_settings()

    # Endpoint nay cong khai tren Internet. Khong co secret thi bat ky ai cung gia
    # duoc update Telegram va dieu khien agent.
    expected = settings.telegram_webhook_secret
    if not expected:
        logger.error("Thieu TELEGRAM_WEBHOOK_SECRET - tu choi tat ca request")
        return Response(status_code=503)
    if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
        x_telegram_bot_api_secret_token, expected
    ):
        logger.warning("Request webhook sai secret token")
        return Response(status_code=403)

    data = await request.json()
    update_id = data.get("update_id")

    # Tra 200 ke ca khi trung: bao Telegram "da nhan roi, dung gui lai nua".
    if update_id is not None and not repository.claim_update(update_id):
        logger.info("Bo qua update %s da xu ly truoc do", update_id)
        return Response(status_code=200)

    application = await _get_application()
    update = Update.de_json(data, application.bot)

    try:
        await application.process_update(update)
    except Exception:
        # Van tra 200: neu tra loi, Telegram se gui lai va gap dung loi nay lan nua.
        logger.exception("Loi khi xu ly update %s", update_id)

    return Response(status_code=200)
