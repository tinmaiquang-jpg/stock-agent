"""Endpoint cho Vercel Cron goi - thay cho APScheduler (serverless khong chay job nen duoc).

Che do chay lien tuc (Docker/VPS) van dung app/scheduler.py; file nay chi phuc vu Vercel.
"""

import hmac
import logging
import os

from fastapi import APIRouter, Header, Request, Response

# Import tu app.alerts chu KHONG phai app.scheduler: file kia keo theo apscheduler,
# package khong co trong bundle Vercel -> function crash luc import.
from app.alerts import check_alerts

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/cron/alerts")
async def cron_check_alerts(
    request: Request,
    authorization: str | None = Header(default=None),
    user_agent: str | None = Header(default=None),
):
    """Vercel Cron goi GET vao day theo lich trong vercel.json.

    Vercel gui user-agent 'vercel-cron/1.0', nhung header do gia duoc, nen neu co dat
    CRON_SECRET thi bat buoc phai khop (Vercel tu gui 'Authorization: Bearer <CRON_SECRET>'
    khi bien nay ton tai). Endpoint nay ban tin nhan Telegram nen khong de mo cho ai cung goi.
    """
    secret = os.environ.get("CRON_SECRET", "")
    if secret:
        expected = f"Bearer {secret}"
        if not authorization or not hmac.compare_digest(authorization, expected):
            logger.warning("Tu choi request cron sai secret")
            return Response(status_code=403)
    elif user_agent != "vercel-cron/1.0":
        logger.warning("Tu choi request cron: chua dat CRON_SECRET va user-agent khong dung")
        return Response(status_code=403)

    await check_alerts()
    return {"ok": True}
