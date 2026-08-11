"""Truy cap du lieu Supabase - tat ca module khac (agent, telegram bot, web admin,
scheduler) deu di qua cac ham o day, khong goi truc tiep supabase client o noi khac."""

from datetime import datetime, timezone
from typing import Any

from app.db.client import get_supabase

# ---------- app_config ----------


def get_config(key: str, default: str | None = None) -> str | None:
    res = get_supabase().table("app_config").select("value").eq("key", key).execute()
    if res.data:
        return res.data[0]["value"]
    return default


def set_config(key: str, value: str) -> None:
    get_supabase().table("app_config").upsert(
        {"key": key, "value": value, "updated_at": datetime.now(timezone.utc).isoformat()}
    ).execute()


def get_all_config() -> dict[str, str]:
    res = get_supabase().table("app_config").select("key, value").execute()
    return {row["key"]: row["value"] for row in res.data}


# ---------- conversations & messages ----------


def get_or_create_conversation(telegram_user_id: int) -> int:
    supabase = get_supabase()
    res = (
        supabase.table("conversations")
        .select("id")
        .eq("telegram_user_id", telegram_user_id)
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    if res.data:
        return res.data[0]["id"]
    created = (
        supabase.table("conversations")
        .insert({"telegram_user_id": telegram_user_id})
        .execute()
    )
    return created.data[0]["id"]


def add_message(conversation_id: int, role: str, content: str) -> None:
    get_supabase().table("messages").insert(
        {"conversation_id": conversation_id, "role": role, "content": content}
    ).execute()


def get_recent_messages(conversation_id: int, limit: int = 20) -> list[dict[str, Any]]:
    res = (
        get_supabase()
        .table("messages")
        .select("role, content, created_at")
        .eq("conversation_id", conversation_id)
        .order("id", desc=True)
        .limit(limit)
        .execute()
    )
    return list(reversed(res.data))


def get_recent_messages_for_admin(limit: int = 100) -> list[dict[str, Any]]:
    res = (
        get_supabase()
        .table("messages")
        .select("role, content, created_at, conversation_id")
        .order("id", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data


# ---------- watchlist ----------


def list_watchlist() -> list[dict[str, Any]]:
    res = get_supabase().table("watchlist").select("*").order("ticker").execute()
    return res.data


def add_watchlist(ticker: str, note: str | None = None) -> None:
    get_supabase().table("watchlist").upsert(
        {"ticker": ticker.upper(), "note": note}, on_conflict="ticker"
    ).execute()


def remove_watchlist(ticker: str) -> None:
    get_supabase().table("watchlist").delete().eq("ticker", ticker.upper()).execute()


# ---------- alerts ----------


def list_alerts(active_only: bool = False) -> list[dict[str, Any]]:
    query = get_supabase().table("alerts").select("*")
    if active_only:
        query = query.eq("active", True)
    return query.order("id", desc=True).execute().data


def create_alert(ticker: str, condition: str, threshold: float) -> dict[str, Any]:
    res = (
        get_supabase()
        .table("alerts")
        .insert({"ticker": ticker.upper(), "condition": condition, "threshold": threshold})
        .execute()
    )
    return res.data[0]


def set_alert_active(alert_id: int, active: bool) -> None:
    get_supabase().table("alerts").update({"active": active}).eq("id", alert_id).execute()


def mark_alert_triggered(alert_id: int) -> None:
    get_supabase().table("alerts").update(
        {"last_triggered_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", alert_id).execute()


def log_alert_trigger(alert_id: int, price: float, message_sent: str) -> None:
    get_supabase().table("alert_log").insert(
        {"alert_id": alert_id, "price_at_trigger": price, "message_sent": message_sent}
    ).execute()
