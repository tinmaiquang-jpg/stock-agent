"""Job nen kiem tra canh bao gia va gui tin nhan Telegram chu dong."""

import logging
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from app.config import get_settings
from app.db import repository
from app.tools import stock_data

logger = logging.getLogger(__name__)

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
# Chi bao lai cung 1 canh bao sau khi da nguoi di it nhat khoang thoi gian nay
RETRIGGER_COOLDOWN_HOURS = 12


def _should_trigger(alert: dict[str, Any], price: dict[str, Any]) -> bool:
    condition = alert["condition"]
    threshold = float(alert["threshold"])

    if condition == "price_above":
        return price["close"] > threshold
    if condition == "price_below":
        return price["close"] < threshold
    if condition == "pct_change":
        pct = price.get("pct_change")
        return pct is not None and abs(pct) >= threshold
    return False


def _in_cooldown(alert: dict[str, Any]) -> bool:
    last = alert.get("last_triggered_at")
    if not last:
        return False
    last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
    hours = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
    return hours < RETRIGGER_COOLDOWN_HOURS


def _format_message(alert: dict[str, Any], price: dict[str, Any]) -> str:
    condition_text = {
        "price_above": f"vuot nguong {alert['threshold']}",
        "price_below": f"xuong duoi nguong {alert['threshold']}",
        "pct_change": f"bien dong tu {alert['threshold']}%",
    }[alert["condition"]]

    return (
        f"CANH BAO {alert['ticker']}: gia {price['close']} nghin VND "
        f"({price['pct_change']:+.2f}% phien {price['date']}) - {condition_text}."
    )


async def check_alerts() -> None:
    alerts = repository.list_alerts(active_only=True)
    if not alerts:
        return

    bot = Bot(token=get_settings().telegram_bot_token)
    owner_id = get_settings().telegram_owner_id

    for alert in alerts:
        if _in_cooldown(alert):
            continue
        try:
            price = stock_data.get_current_price(alert["ticker"])
        except stock_data.StockDataError as exc:
            logger.warning("Bo qua canh bao #%s: %s", alert["id"], exc)
            continue

        if not _should_trigger(alert, price):
            continue

        message = _format_message(alert, price)
        try:
            await bot.send_message(chat_id=owner_id, text=message)
        except Exception:
            logger.exception("Khong gui duoc canh bao #%s qua Telegram", alert["id"])
            continue

        repository.mark_alert_triggered(alert["id"])
        repository.log_alert_trigger(alert["id"], price["close"], message)
        logger.info("Da gui canh bao #%s cho %s", alert["id"], alert["ticker"])


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=VN_TZ)
    # Gio giao dich HOSE: 09:00-15:00 cac ngay trong tuan. Chay moi 15 phut.
    scheduler.add_job(
        check_alerts,
        CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/15", timezone=VN_TZ),
        id="check_alerts",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
