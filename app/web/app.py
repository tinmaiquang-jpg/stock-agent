"""Factory tao FastAPI app cho web admin.

Tach rieng khoi app/main.py vi web admin deploy duoc len serverless (Vercel) mot minh:
no chi can fastapi + jinja2 + supabase (~2MB), KHONG import claude-agent-sdk (273MB,
vuot gioi han 250MB cua Vercel), vnstock, pandas hay telegram.

Config nam trong Supabase nen doi prompt/model tren Vercel co hieu luc ngay voi con bot
dang chay o noi khac - khong can restart, khong can deploy lai.
"""

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.web.routes import router


def create_admin_app(**fastapi_kwargs) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Stock Agent Admin", **fastapi_kwargs)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.app_secret_key,
        # Tren Internet cong khai cookie phai chi gui qua HTTPS. Mac dinh True (an toan
        # cho moi deploy moi); .env local dat SESSION_HTTPS_ONLY=false de test qua http.
        https_only=settings.session_https_only,
        same_site="lax",
    )
    app.include_router(router)
    return app
