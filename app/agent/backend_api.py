"""Backend 'api_key': goi Messages API truc tiep bang CLAUDE_API_KEY, tinh tien theo token.

Vong lap tool-use: nhan tin nhan -> goi Claude -> chay tool neu can -> tra ket qua lai
-> lay cau tra loi cuoi cung."""

import logging
from functools import lru_cache

import anthropic

from app.agent import settings_store
from app.agent.tools import TOOL_SCHEMAS, execute_tool
from app.config import get_settings

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 8
MAX_TOKENS = 8000


@lru_cache
def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=get_settings().claude_api_key)


def run_agent(user_message: str, history: list[dict[str, str]] | None = None) -> str:
    """Tra ve cau tra loi cuoi cung cua agent duoi dang text."""
    config = settings_store.load()
    system_prompt, model, effort = config.system_prompt, config.model, config.effort

    messages: list[dict] = [
        {"role": m["role"], "content": m["content"]} for m in (history or [])
    ]
    messages.append({"role": "user", "content": user_message})
    usage = _UsageTally()

    for _ in range(MAX_TOOL_ROUNDS):
        response = _client().messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            # Cache tools + system prompt (~2k token co dinh). tools render truoc
            # system, nen 1 breakpoint o cuoi system cache duoc ca hai. Cache TTL 5
            # phut: giup nhieu trong 1 luot chat (2-3 lan goi API lien tiep), khong
            # giup giua cac tin nhan cach nhau vai gio.
            system=[
                {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
            ],
            output_config={"effort": effort},
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        usage.add(response.usage)

        if response.stop_reason == "refusal":
            usage.log(model)
            return "Yeu cau nay bi tu choi vi ly do an toan. Ban thu dien dat lai giup minh nhe."

        if response.stop_reason != "tool_use":
            usage.log(model)
            return _extract_text(response) or "(Agent khong tra ve noi dung)"

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            logger.info("Chay tool %s voi input %s", block.name, block.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": execute_tool(block.name, block.input),
                }
            )
        messages.append({"role": "user", "content": tool_results})

    usage.log(model)
    return "Agent da goi tool qua nhieu lan ma chua ket luan duoc. Ban thu hoi cu the hon nhe."


def _extract_text(response) -> str:
    return "\n".join(b.text for b in response.content if b.type == "text").strip()


class _UsageTally:
    """Cong don token qua cac lan goi API trong 1 luot chat de theo doi chi phi.

    cache_read > 0 nghia la prompt caching dang co tac dung. Neu cache_creation > 0
    ma cache_read luon = 0, kiem tra lai: Haiku 4.5 yeu cau prefix >= 4096 token moi
    cache duoc (Sonnet 5 la 1024, Opus 5 la 512) - prefix cua app nay ~2k nen tren
    Haiku 4.5 caching se im lang khong hoat dong.
    """

    def __init__(self) -> None:
        self.calls = 0
        self.input = 0
        self.output = 0
        self.cache_write = 0
        self.cache_read = 0

    def add(self, u) -> None:
        self.calls += 1
        self.input += u.input_tokens
        self.output += u.output_tokens
        self.cache_write += getattr(u, "cache_creation_input_tokens", 0) or 0
        self.cache_read += getattr(u, "cache_read_input_tokens", 0) or 0

    def log(self, model: str) -> None:
        logger.info(
            "Token [%s] %d lan goi API: input=%d output=%d cache_write=%d cache_read=%d",
            model,
            self.calls,
            self.input,
            self.output,
            self.cache_write,
            self.cache_read,
        )
