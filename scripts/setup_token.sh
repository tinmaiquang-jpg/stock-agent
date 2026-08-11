#!/usr/bin/env bash
# Sinh OAuth token dai han (1 nam) tu goi Claude Pro/Max/Team/Enterprise, de backend
# 'subscription' dung ma khong can API key.
#
# Lenh nay se mo browser cho ban dang nhap va duyet quyen. Token in ra terminal va
# KHONG duoc luu o dau ca - copy no vao CLAUDE_CODE_OAUTH_TOKEN trong .env (local)
# hoac vao Variables tren Railway (production).
#
# Dung binary Claude Code di kem package claude-agent-sdk, nen khong can cai Node.js.

set -euo pipefail

cd "$(dirname "$0")/.."

BIN=$(find .venv/lib/python*/site-packages/claude_agent_sdk/_bundled -name claude -type f 2>/dev/null | head -1)

if [[ -z "${BIN:-}" || ! -x "$BIN" ]]; then
  echo "Khong tim thay binary Claude Code." >&2
  echo "Cai dependency truoc: uv pip install -r requirements.txt" >&2
  exit 1
fi

echo "Dang mo browser de dang nhap Claude..."
echo "Sau khi duyet quyen, token se in ra ngay duoi day."
echo
exec "$BIN" setup-token
