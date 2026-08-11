"""Cau hinh agent doc tu Supabase (sua duoc tren web admin), dung chung cho ca 2 backend."""

from dataclasses import dataclass

from app.config import get_settings
from app.db import repository

DEFAULT_SYSTEM_PROMPT = (
    "Ban la tro ly ca nhan theo doi va phan tich chung khoan Viet Nam. Dung tool de lay "
    "du lieu thuc te truoc khi tra loi - khong doan gia. Tra loi ngan gon bang tieng Viet."
)

# 'subscription' = Claude Agent SDK + CLAUDE_CODE_OAUTH_TOKEN (dung goi Pro/Max, khong ton
# tien API). 'api_key' = Messages API + CLAUDE_API_KEY (tinh tien theo token).
BACKENDS = ("subscription", "api_key")
DEFAULT_BACKEND = "subscription"


@dataclass(frozen=True)
class AgentConfig:
    system_prompt: str
    model: str
    effort: str
    backend: str


def load() -> AgentConfig:
    config = repository.get_all_config()
    backend = config.get("llm_backend") or DEFAULT_BACKEND
    if backend not in BACKENDS:
        backend = DEFAULT_BACKEND
    return AgentConfig(
        system_prompt=config.get("system_prompt") or DEFAULT_SYSTEM_PROMPT,
        model=config.get("model") or get_settings().claude_model,
        effort=config.get("effort") or "medium",
        backend=backend,
    )
