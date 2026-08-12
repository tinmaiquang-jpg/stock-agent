"""Entrypoint Vercel - chay CA HE THONG tren Vercel:

- Web admin (cau hinh, watchlist, alerts, nhat ky)
- Telegram bot o che do webhook (POST /telegram/webhook)
- Cron canh bao gia (GET /api/cron/alerts)

Khac biet so voi chay lien tuc (Docker/VPS): khong co polling va khong co APScheduler,
vi serverless khong giu process song giua cac request.

Han che cua goi Hobby: cron chi chay 1 lan/ngay. Muon canh bao gia moi 15 phut trong
gio giao dich thi phai len goi Pro, hoac chay phan scheduler o Railway/VPS.
"""

import os
import tempfile

# Filesystem cua Vercel chi doc, tru /tmp. Binary Claude Code (do claude-agent-sdk
# spawn) can ghi config va transcript, mac dinh vao ~/.claude -> se loi. Tro no sang
# /tmp TRUOC khi import bat ky module nao cham toi SDK.
if os.environ.get("VERCEL"):
    _tmp = tempfile.gettempdir()
    # Gan de (khong dung setdefault): Vercel DA dat san HOME tro vao thu muc chi doc,
    # nen setdefault se khong ghi de va cac thu vien van co ghi vao do roi loi.
    os.environ["HOME"] = _tmp
    os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(_tmp, ".claude")
    os.environ["XDG_CONFIG_HOME"] = os.path.join(_tmp, ".config")
    os.environ["XDG_CACHE_HOME"] = os.path.join(_tmp, ".cache")

from app.telegram_bot.webhook import router as telegram_router  # noqa: E402
from app.web.app import create_admin_app  # noqa: E402
from app.web.cron import router as cron_router  # noqa: E402

app = create_admin_app()
app.include_router(telegram_router)
app.include_router(cron_router)
