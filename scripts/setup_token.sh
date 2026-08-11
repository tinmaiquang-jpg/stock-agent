#!/usr/bin/env bash
# Sinh OAuth token dai han (1 nam) tu goi Claude Pro/Max/Team/Enterprise, de backend
# 'subscription' dung ma khong can API key.
#
# Script se mo browser cho ban dang nhap, roi TU DONG ghi token vao CLAUDE_CODE_OAUTH_TOKEN
# trong .env - khong can copy-paste thu cong.
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

if [[ ! -f .env ]]; then
  echo "Khong thay file .env. Tao truoc: cp .env.example .env" >&2
  exit 1
fi

OUT=$(mktemp)
trap 'rm -f "$OUT"' EXIT

echo "Dang mo browser de dang nhap Claude..."
echo "Duyet quyen tren browser, roi quay lai day."
echo

# tee: van hien output tren terminal (de ban thay prompt va dan code neu can),
# dong thoi luu lai de tach token ra.
"$BIN" setup-token 2>&1 | tee "$OUT"

TOKEN=$(grep -oE 'sk-ant-oat[A-Za-z0-9_-]+' "$OUT" | tail -1 || true)

if [[ -z "$TOKEN" ]]; then
  echo
  echo "Khong tim thay token trong output." >&2
  echo "Token phai la chuoi bat dau bang 'sk-ant-oat'. Neu ban thay no o tren ma script" >&2
  echo "khong bat duoc, dan thu cong vao dong CLAUDE_CODE_OAUTH_TOKEN= trong .env." >&2
  exit 1
fi

# Ghi vao .env: thay dong cu neu co, khong thi them moi.
if grep -q '^CLAUDE_CODE_OAUTH_TOKEN=' .env; then
  # Dung awk thay vi sed -i: token co the chua ky tu sed hieu la delimiter.
  awk -v tok="$TOKEN" '
    /^CLAUDE_CODE_OAUTH_TOKEN=/ { print "CLAUDE_CODE_OAUTH_TOKEN=" tok; next }
    { print }
  ' .env > .env.tmp && mv .env.tmp .env
else
  printf '\nCLAUDE_CODE_OAUTH_TOKEN=%s\n' "$TOKEN" >> .env
fi

echo
echo "Da ghi token vao .env (${#TOKEN} ky tu, bat dau ${TOKEN:0:14})."
echo "Token het han sau 1 nam. Chay lai script nay de gia han."
