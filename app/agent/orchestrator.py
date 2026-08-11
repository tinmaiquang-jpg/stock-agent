"""Chon backend LLM theo cau hinh (sua duoc tren web admin), roi goi backend do.

- 'subscription': Claude Agent SDK + CLAUDE_CODE_OAUTH_TOKEN (goi Pro/Max, khong ton tien API)
- 'api_key': Messages API + CLAUDE_API_KEY (tinh tien theo token)

Ca 2 backend dung chung 10 tool trong app/agent/tools.py, nen doi backend khong thay doi
kha nang cua agent.
"""

import logging

from app.agent import settings_store

logger = logging.getLogger(__name__)


def run_agent(user_message: str, history: list[dict[str, str]] | None = None) -> str:
    backend = settings_store.load().backend

    if backend == "subscription":
        from app.agent import backend_sdk

        return backend_sdk.run_agent(user_message, history)

    from app.agent import backend_api

    return backend_api.run_agent(user_message, history)
