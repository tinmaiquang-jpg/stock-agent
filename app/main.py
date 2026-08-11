"""Diem khoi dong: 1 process chay dong thoi web admin (FastAPI), Telegram bot
(polling) va scheduler canh bao."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.scheduler import build_scheduler
from app.telegram_bot.bot import build_application
from app.web.app import create_admin_app

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    telegram_app = build_application()
    scheduler = build_scheduler()

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling(drop_pending_updates=True)
    scheduler.start()
    logger.info("Telegram bot (polling) va scheduler da chay")

    yield

    scheduler.shutdown(wait=False)
    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()
    logger.info("Da dung bot va scheduler")


# Cung web admin nhu ban deploy tren Vercel, cong them lifespan chay bot + scheduler.
app = create_admin_app(lifespan=lifespan)
