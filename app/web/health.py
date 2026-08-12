"""Trang chan doan cau hinh - bao bien moi truong nao thieu hoac hong.

Ly do can: loi cau hinh tren serverless chi lo ra khi co request that, va phai vao
dashboard doc log moi biet. Vi du da gap: CLAUDE_CODE_OAUTH_TOKEN bi lan mot ky tu
non-ASCII luc copy-paste, agent chet o buoc xac thuc nhung ben ngoai chi thay bot
"khong tra loi".

KHONG bao gio tra ve gia tri that, chi tra do dai va cac kiem tra dinh dang.
"""

import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import get_settings
from app.web.auth import is_authenticated

router = APIRouter()

# (ten bien, bat buoc de bot chay?, tien to mong doi)
CHECKS = [
    ("CLAUDE_CODE_OAUTH_TOKEN", True, "sk-ant-oat"),
    ("TELEGRAM_BOT_TOKEN", True, None),
    ("TELEGRAM_OWNER_ID", True, None),
    ("TELEGRAM_WEBHOOK_SECRET", True, None),
    ("SUPABASE_URL", True, "https://"),
    ("SUPABASE_KEY", True, None),
    ("ADMIN_PASSWORD_HASH", True, None),
    ("APP_SECRET_KEY", True, None),
    ("CRON_SECRET", False, None),
    ("CLAUDE_API_KEY", False, "sk-ant-api"),
]


def _inspect(name: str, expected_prefix: str | None) -> dict:
    value = os.environ.get(name, "")
    if not value:
        # Chay local thi gia tri nam trong .env chu khong o os.environ
        value = str(getattr(get_settings(), name.lower(), "") or "")

    if not value:
        return {"set": False}

    non_ascii = [
        {"position": i, "char": repr(c), "code": hex(ord(c))}
        for i, c in enumerate(value)
        if ord(c) > 127
    ]
    result = {
        "set": True,
        "length": len(value),
        "ascii_ok": not non_ascii,
        "has_whitespace": value != value.strip(),
        "preview": value[:10] + "..." if len(value) > 10 else "***",
    }
    if non_ascii:
        result["non_ascii"] = non_ascii[:5]
    if expected_prefix:
        result["prefix_ok"] = value.startswith(expected_prefix)
    return result


@router.get("/health")
async def health(request: Request):
    """Yeu cau dang nhap: do dai va tien to cua secret cung la thong tin nen che."""
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)

    report = {name: _inspect(name, prefix) for name, required, prefix in CHECKS}
    problems = []
    for name, required, _ in CHECKS:
        info = report[name]
        if required and not info["set"]:
            problems.append(f"{name}: CHUA DAT")
        elif info.get("set"):
            if not info.get("ascii_ok", True):
                problems.append(f"{name}: co ky tu non-ASCII (thuong do copy-paste)")
            if info.get("has_whitespace"):
                problems.append(f"{name}: co khoang trang thua o dau/cuoi")
            if info.get("prefix_ok") is False:
                problems.append(f"{name}: sai tien to mong doi")

    return JSONResponse(
        {"ok": not problems, "problems": problems, "variables": report}
    )
