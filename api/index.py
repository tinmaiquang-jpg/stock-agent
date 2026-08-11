"""Entrypoint cho Vercel - CHI chay web admin (config, watchlist, alerts, logs).

Con bot Telegram, scheduler va agent KHONG chay o day: chung can process song lien tuc
va claude-agent-sdk nang 273MB (vuot gioi han 250MB cua Vercel serverless function).
Nhung phan do deploy tren Railway/VPS - xem DEPLOY.md.

Ca hai noi dung chung 1 Supabase, nen thay doi cau hinh o day co hieu luc ngay voi bot.
"""

from app.web.app import create_admin_app

app = create_admin_app()
