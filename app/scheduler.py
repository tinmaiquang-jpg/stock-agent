"""Job nen chay canh bao gia dinh ky - chi dung o che do chay lien tuc (Docker/VPS).

Tren Vercel khong co process song lien tuc, nen viec nay do Vercel Cron goi
app/web/cron.py. Logic kiem tra nam o app/alerts.py, dung chung cho ca hai che do.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.alerts import VN_TZ, check_alerts


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
