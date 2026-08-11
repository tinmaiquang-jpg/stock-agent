"""Telegram bot o che do polling (khong can domain/SSL - chay duoc ngay tren local).
Chi phan hoi TELEGRAM_OWNER_ID; moi nguoi khac bi tu choi."""

import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.agent.backend_sdk import NOT_LOGGED_IN_HINT, AuthError
from app.agent.memory import chat
from app.config import get_settings
from app.db import repository

logger = logging.getLogger(__name__)

WELCOME = (
    "Xin chao! Minh la tro ly theo doi chung khoan Viet Nam cua ban.\n\n"
    "Cu nhan tin tu nhien, vi du:\n"
    "- Gia FPT hom nay the nao?\n"
    "- Them VCB vao watchlist\n"
    "- Canh bao khi VNM xuong duoi 60\n"
    "- Phan tich chi so tai chinh cua HPG\n\n"
    "Lenh nhanh: /watchlist, /alerts"
)


def _is_owner(update: Update) -> bool:
    user = update.effective_user
    return user is not None and user.id == get_settings().telegram_owner_id


async def _reject(update: Update) -> None:
    logger.warning("Tu choi user khong phai chu: %s", update.effective_user)
    if update.message:
        await update.message.reply_text("Bot nay chi danh cho chu so huu.")


async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_owner(update):
        return await _reject(update)
    await update.message.reply_text(WELCOME)


async def cmd_watchlist(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_owner(update):
        return await _reject(update)
    items = await asyncio.to_thread(repository.list_watchlist)
    if not items:
        await update.message.reply_text("Watchlist dang trong. Nhan tin 'them FPT vao watchlist'.")
        return
    lines = [f"- {i['ticker']}" + (f" ({i['note']})" if i.get("note") else "") for i in items]
    await update.message.reply_text("Watchlist:\n" + "\n".join(lines))


async def cmd_alerts(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_owner(update):
        return await _reject(update)
    items = await asyncio.to_thread(repository.list_alerts, True)
    if not items:
        await update.message.reply_text("Chua co canh bao nao dang bat.")
        return
    lines = [f"- #{a['id']} {a['ticker']} {a['condition']} {a['threshold']}" for a in items]
    await update.message.reply_text("Canh bao dang bat:\n" + "\n".join(lines))


async def on_message(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_owner(update):
        return await _reject(update)
    if not update.message or not update.message.text:
        return

    await update.message.chat.send_action("typing")
    try:
        # Agent goi Claude + vnstock dong bo, chay o thread khac de khong block event loop
        reply = await asyncio.to_thread(chat, update.effective_user.id, update.message.text)
    except AuthError:
        logger.exception("Agent SDK chua duoc xac thuc")
        await update.message.reply_text(NOT_LOGGED_IN_HINT)
        return
    except Exception:
        logger.exception("Loi khi xu ly tin nhan")
        await update.message.reply_text("Co loi khi xu ly. Ban thu lai sau it phut nhe.")
        return

    await update.message.reply_text(reply)


def build_application() -> Application:
    app = Application.builder().token(get_settings().telegram_bot_token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("watchlist", cmd_watchlist))
    app.add_handler(CommandHandler("alerts", cmd_alerts))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    return app
