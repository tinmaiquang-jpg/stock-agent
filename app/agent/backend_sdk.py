"""Backend 'subscription': dung Claude Agent SDK, xac thuc bang CLAUDE_CODE_OAUTH_TOKEN
(sinh boi `claude setup-token`, yeu cau goi Pro/Max/Team/Enterprise) - khong ton tien API.

Khac biet so voi backend_api:
- Agent SDK spawn 1 process con (binary Claude Code di kem package, khong can Node.js),
  nen cham hon va nang hon mot chut.
- Tool cua ta duoc expose qua in-process MCP server, ten day du la mcp__stock__<ten_tool>.
- Toan bo built-in tool (Bash/Read/Write/Edit/WebSearch...) bi tat bang tools=[]: agent
  KHONG co quyen truy cap shell hay file he thong, chi goi duoc 10 tool cua ta.
- Lich su hoi thoai van luu o Supabase (nguon su that), duoc render vao prompt. Khong dung
  session tren dia cua SDK vi filesystem tren Railway la ephemeral, redeploy la mat.
"""

import asyncio
import json
import logging
from functools import lru_cache
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

from app.agent import settings_store
from app.agent.tools import TOOL_SCHEMAS, execute_tool
from app.config import get_settings

logger = logging.getLogger(__name__)

MCP_SERVER_NAME = "stock"
MAX_TURNS = 12


def _make_handler(tool_name: str):
    """Bao execute_tool (dong bo) thanh handler async ma Agent SDK yeu cau."""

    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        logger.info("Chay tool %s voi input %s", tool_name, args)
        # execute_tool goi vnstock/Supabase dong bo -> day sang thread khac de khong
        # block event loop cua SDK.
        result = await asyncio.to_thread(execute_tool, tool_name, args)
        is_error = '"error"' in result[:20]
        return {"content": [{"type": "text", "text": result}], "is_error": is_error}

    handler.__name__ = f"tool_{tool_name}"
    return handler


@lru_cache
def _server():
    """Dung chung 1 MCP server cho ca process; tao tu cung TOOL_SCHEMAS nhu backend_api
    nen 2 backend luon co dung 1 bo tool."""
    tools = [
        tool(schema["name"], schema["description"], schema.get("input_schema", {}))(
            _make_handler(schema["name"])
        )
        for schema in TOOL_SCHEMAS
    ]
    return create_sdk_mcp_server(name=MCP_SERVER_NAME, version="1.0.0", tools=tools)


def _render_prompt(user_message: str, history: list[dict[str, str]] | None) -> str:
    """Ghep lich su vao prompt. Agent SDK nhan prompt dang chuoi, nen lich su duoc render
    thanh transcript thay vi truyen theo role nhu Messages API."""
    if not history:
        return user_message

    lines = ["<lich_su_hoi_thoai>"]
    for m in history:
        who = "Nguoi dung" if m["role"] == "user" else "Tro ly"
        lines.append(f"{who}: {m['content']}")
    lines.append("</lich_su_hoi_thoai>")
    lines.append("")
    lines.append(f"Tin nhan moi cua nguoi dung: {user_message}")
    return "\n".join(lines)


def _sdk_env() -> dict[str, str]:
    """Truyen token vao subprocess ma SDK spawn.

    SDK doc CLAUDE_CODE_OAUTH_TOKEN tu moi truong cua subprocess, con token cua ta nam
    trong .env (pydantic-settings doc vao Settings chu khong export ra os.environ). Neu
    khong truyen tay o day, SDK bao "Not logged in" du .env da co token.
    """
    token = get_settings().claude_code_oauth_token.strip()
    return {"CLAUDE_CODE_OAUTH_TOKEN": token} if token else {}


def _build_options(config: settings_store.AgentConfig) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=config.model,
        effort=config.effort,
        env=_sdk_env(),
        # Chuoi thuan = CHI dung system prompt cua ta, khong keo theo prompt cua Claude Code
        system_prompt=config.system_prompt,
        # Tat toan bo built-in tool. Agent chi con 10 tool cua ta.
        tools=[],
        mcp_servers={MCP_SERVER_NAME: _server()},
        allowed_tools=[f"mcp__{MCP_SERVER_NAME}__{s['name']}" for s in TOOL_SCHEMAS],
        # Khong hoi quyen (server chay khong co nguoi truc). Khong dung
        # bypassPermissions: allowed_tools da liet ke du 10 tool va built-in da tat,
        # nen khong can mo quyen rong hon muc can thiet.
        permission_mode="dontAsk",
        max_turns=MAX_TURNS,
        # Khong doc CLAUDE.md / settings cua may, tranh hanh vi khac nhau giua local va VPS
        setting_sources=[],
    )


class AuthError(RuntimeError):
    """Chua co credential hop le cho Agent SDK."""


NOT_LOGGED_IN_HINT = (
    "Agent SDK chua duoc xac thuc. Tren may co browser, chay lenh sau (binary di kem "
    "package, khong can cai Node.js):\n"
    "  ./scripts/setup_token.sh\n"
    "roi dat token vao bien moi truong CLAUDE_CODE_OAUTH_TOKEN. Hoac doi backend sang "
    "'api_key' tren web admin va dien CLAUDE_API_KEY."
)


def _is_auth_failure(text: str) -> bool:
    lowered = text.lower()
    return "not logged in" in lowered or "login expired" in lowered or "/login" in lowered


async def _run(user_message: str, history: list[dict[str, str]] | None) -> str:
    config = settings_store.load()
    prompt = _render_prompt(user_message, history)

    final_text = ""
    fallback_text: list[str] = []
    # Khong raise ben trong `async for`: lam vay dong generator khi no dang chay va sinh
    # "RuntimeError: aclose(): asynchronous generator is already running". Ghi lai loi roi
    # raise sau khi vong lap ket thuc.
    pending_error: str | None = None

    try:
        async for message in query(prompt=prompt, options=_build_options(config)):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        fallback_text.append(block.text)
            elif isinstance(message, ResultMessage):
                logger.info(
                    "Agent SDK [%s] ket thuc: subtype=%s is_error=%s turns=%s cost_usd=%s",
                    config.model,
                    message.subtype,
                    getattr(message, "is_error", None),
                    getattr(message, "num_turns", None),
                    getattr(message, "total_cost_usd", None),
                )
                # Luu y: SDK co the tra subtype='success' NHUNG is_error=True (vd chua
                # dang nhap), nen phai kiem tra ca hai.
                if getattr(message, "is_error", False):
                    pending_error = (message.result or "").strip() or message.subtype
                elif message.result:
                    final_text = message.result
    except Exception as exc:
        # Sau ResultMessage loi, SDK con tu raise Exception. Neu da ghi nhan loi o tren thi
        # bo qua exception nay; neu chua thi dung no lam nguyen nhan.
        if pending_error is None:
            pending_error = str(exc)

    if pending_error is not None:
        if _is_auth_failure(pending_error) or _is_auth_failure("\n".join(fallback_text)):
            raise AuthError(pending_error)
        raise RuntimeError(f"Agent SDK loi: {pending_error}")

    return final_text or "\n".join(fallback_text).strip() or "(Agent khong tra ve noi dung)"


def run_agent(user_message: str, history: list[dict[str, str]] | None = None) -> str:
    """Interface dong bo giong backend_api de bot/scheduler goi khong can biet backend nao.

    Ham nay duoc goi tu worker thread (telegram bot dung asyncio.to_thread), nen thread do
    chua co event loop -> asyncio.run an toan.
    """
    try:
        return asyncio.run(_run(user_message, history))
    except Exception:
        logger.exception("Loi khi chay Agent SDK")
        raise


def describe_json_schemas() -> str:
    """Tien ich debug: in ra ten tool day du ma Claude nhin thay."""
    return json.dumps(
        [f"mcp__{MCP_SERVER_NAME}__{s['name']}" for s in TOOL_SCHEMAS], ensure_ascii=False
    )
