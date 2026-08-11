"""Route cho web admin: dang nhap, dashboard, cau hinh prompt/model, watchlist,
canh bao, nhat ky hoi thoai."""

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.agent import settings_store
from app.db import repository
from app.web.auth import SESSION_KEY, check_credentials, is_authenticated

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

LOGIN_REDIRECT = RedirectResponse(url="/login", status_code=303)


def _require_auth(request: Request) -> RedirectResponse | None:
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if not check_credentials(username, password):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Sai tai khoan hoac mat khau"}, status_code=401
        )
    request.session[SESSION_KEY] = True
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if redirect := _require_auth(request):
        return redirect
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "config": repository.get_all_config(),
            "watchlist_count": len(repository.list_watchlist()),
            "active_alerts": len(repository.list_alerts(active_only=True)),
        },
    )


@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request, saved: bool = False):
    if redirect := _require_auth(request):
        return redirect
    return templates.TemplateResponse(
        request, "config.html", {"config": repository.get_all_config(), "saved": saved}
    )


@router.post("/config")
async def config_save(
    request: Request,
    system_prompt: str = Form(...),
    model: str = Form(...),
    effort: str = Form(...),
    max_history_messages: str = Form(...),
    llm_backend: str = Form(...),
):
    if redirect := _require_auth(request):
        return redirect
    if llm_backend not in settings_store.BACKENDS:
        llm_backend = settings_store.DEFAULT_BACKEND
    repository.set_config("system_prompt", system_prompt)
    repository.set_config("model", model)
    repository.set_config("effort", effort)
    repository.set_config("max_history_messages", max_history_messages)
    repository.set_config("llm_backend", llm_backend)
    return RedirectResponse(url="/config?saved=true", status_code=303)


@router.get("/watchlist", response_class=HTMLResponse)
async def watchlist_page(request: Request):
    if redirect := _require_auth(request):
        return redirect
    return templates.TemplateResponse(
        request, "watchlist.html", {"items": repository.list_watchlist()}
    )


@router.post("/watchlist/add")
async def watchlist_add(request: Request, ticker: str = Form(...), note: str = Form("")):
    if redirect := _require_auth(request):
        return redirect
    repository.add_watchlist(ticker, note or None)
    return RedirectResponse(url="/watchlist", status_code=303)


@router.post("/watchlist/remove")
async def watchlist_remove(request: Request, ticker: str = Form(...)):
    if redirect := _require_auth(request):
        return redirect
    repository.remove_watchlist(ticker)
    return RedirectResponse(url="/watchlist", status_code=303)


@router.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request):
    if redirect := _require_auth(request):
        return redirect
    return templates.TemplateResponse(request, "alerts.html", {"items": repository.list_alerts()})


@router.post("/alerts/add")
async def alerts_add(
    request: Request,
    ticker: str = Form(...),
    condition: str = Form(...),
    threshold: float = Form(...),
):
    if redirect := _require_auth(request):
        return redirect
    repository.create_alert(ticker, condition, threshold)
    return RedirectResponse(url="/alerts", status_code=303)


@router.post("/alerts/toggle")
async def alerts_toggle(request: Request, alert_id: int = Form(...), active: str = Form(...)):
    if redirect := _require_auth(request):
        return redirect
    repository.set_alert_active(alert_id, active == "true")
    return RedirectResponse(url="/alerts", status_code=303)


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    if redirect := _require_auth(request):
        return redirect
    return templates.TemplateResponse(
        request, "logs.html", {"messages": repository.get_recent_messages_for_admin(limit=100)}
    )
