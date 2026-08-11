"""Bo nho hoi thoai: luu/doc lich su chat tu Supabase de agent co ngu canh giua cac
lan chat va khong mat khi restart app."""

from app.agent.orchestrator import run_agent
from app.db import repository

DEFAULT_HISTORY_LIMIT = 20


def chat(telegram_user_id: int, user_message: str) -> str:
    """Xu ly 1 luot chat: doc lich su -> goi agent -> luu ca 2 tin nhan."""
    conversation_id = repository.get_or_create_conversation(telegram_user_id)

    limit_raw = repository.get_config("max_history_messages")
    limit = int(limit_raw) if limit_raw and limit_raw.isdigit() else DEFAULT_HISTORY_LIMIT
    history = repository.get_recent_messages(conversation_id, limit=limit)

    reply = run_agent(user_message, history=history)

    repository.add_message(conversation_id, "user", user_message)
    repository.add_message(conversation_id, "assistant", reply)
    return reply
