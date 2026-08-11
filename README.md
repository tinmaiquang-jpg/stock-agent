# Trợ lý cá nhân theo dõi chứng khoán Việt Nam

AI agent cá nhân: chat qua **Telegram**, quản trị qua **website admin**, bộ não là **Claude API**,
bộ nhớ lưu ở **Supabase**, dữ liệu chứng khoán VN lấy từ `vnstock` (miễn phí, không cần tài khoản broker).

**Phạm vi:** chỉ theo dõi / phân tích / cảnh báo giá. Không đặt lệnh mua bán thật.

## Kiến trúc

```
Telegram  ─┐
           ├─▶  FastAPI app (1 process)  ─▶  Claude API (tool use)
Browser   ─┘     ├─ web admin routes      ─▶  vnstock (giá, lịch sử, BCTC)
                 ├─ telegram bot (polling)
                 └─ APScheduler (check cảnh báo mỗi 15' giờ giao dịch)
                              │
                              ▼
                     Supabase (Postgres cloud)
```

## Cấu trúc code

| Đường dẫn | Vai trò |
|---|---|
| [app/main.py](app/main.py) | Khởi động web + bot + scheduler trong 1 process |
| [app/config.py](app/config.py) | Đọc biến môi trường từ `.env` |
| [app/tools/stock_data.py](app/tools/stock_data.py) | Lấy dữ liệu chứng khoán VN qua `vnstock` v4 |
| [app/agent/tools.py](app/agent/tools.py) | Định nghĩa 10 tool + dispatch (dùng chung cho cả 2 backend) |
| [app/agent/orchestrator.py](app/agent/orchestrator.py) | Chọn backend theo cấu hình |
| [app/agent/backend_sdk.py](app/agent/backend_sdk.py) | Backend `subscription` — Claude Agent SDK |
| [app/agent/backend_api.py](app/agent/backend_api.py) | Backend `api_key` — Messages API |
| [app/agent/settings_store.py](app/agent/settings_store.py) | Đọc cấu hình agent từ Supabase |
| [app/agent/memory.py](app/agent/memory.py) | Lưu/đọc lịch sử hội thoại |
| [app/telegram_bot/bot.py](app/telegram_bot/bot.py) | Bot Telegram, chỉ trả lời chính chủ |
| [app/web/routes.py](app/web/routes.py) | Web admin: config, watchlist, alerts, logs |
| [app/scheduler.py](app/scheduler.py) | Job kiểm tra cảnh báo giá |
| [app/db/repository.py](app/db/repository.py) | Tất cả truy cập Supabase đi qua đây |
| [migrations/001_init.sql](migrations/001_init.sql) | Schema database |

---

## Cài đặt (local)

### Bước 1 — Môi trường Python

Project cần Python 3.10+. Máy này đã có sẵn `uv` + Python 3.12 và virtualenv `.venv`.
Nếu cần tạo lại từ đầu:

```bash
uv venv --python 3.12 && uv pip install -r requirements.txt
```

### Bước 2 — Tạo project Supabase

1. Vào https://supabase.com → tạo project mới (free tier là đủ).
2. Mở **SQL Editor** → **New query** → dán toàn bộ nội dung [migrations/001_init.sql](migrations/001_init.sql) → **Run**.
3. Vào **Project Settings → API**, copy:
   - `Project URL` → điền vào `SUPABASE_URL` trong `.env`
   - `service_role` secret key → điền vào `SUPABASE_KEY` trong `.env`

> Dùng `service_role` key vì app chạy ở backend (không expose ra browser). Đừng đưa key này vào code frontend.

### Bước 3 — Điền `.env`

File `.env` đã có sẵn Telegram bot token. Cần điền thêm:

| Biến | Lấy ở đâu |
|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | Chạy `./scripts/setup_token.sh` (cần gói Claude Pro/Max) |
| `TELEGRAM_OWNER_ID` | Chat với [@userinfobot](https://t.me/userinfobot) trên Telegram, nó trả về user id dạng số |
| `SUPABASE_URL`, `SUPABASE_KEY` | Bước 2 |
| `ADMIN_PASSWORD_HASH`, `APP_SECRET_KEY` | Chạy lệnh dưới đây rồi dán kết quả vào `.env` |

`CLAUDE_API_KEY` chỉ cần nếu bạn đổi backend sang `api_key` — xem mục
[Hai backend LLM](#hai-backend-llm--chọn-trên-web-admin).

```bash
.venv/bin/python scripts/make_secrets.py 'mat-khau-admin-cua-ban'
```

### Bước 4 — Chạy

```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
```

- Web admin: http://localhost:8000 (đăng nhập bằng `ADMIN_USERNAME` + mật khẩu ở bước 3)
- Telegram: mở bot của bạn, gửi `/start`

---

## Kiểm thử

**Dữ liệu chứng khoán (không cần Supabase / Telegram):**

```bash
.venv/bin/python scripts/test_stock_data.py
```

**End-to-end:** trên Telegram thử lần lượt

1. `Giá FPT hôm nay thế nào?` → agent gọi tool `get_price`, trả về giá thật
2. `Thêm VCB vào watchlist` → kiểm tra lại bằng `/watchlist`
3. `Cảnh báo khi VNM xuống dưới 60` → kiểm tra ở trang **Cảnh báo** trên web admin
4. `Phân tích chỉ số tài chính của HPG` → agent gọi `get_financial_ratios`

**Web admin:** vào **Cấu hình**, sửa system prompt → chat lại trên Telegram, xác nhận bot phản hồi theo prompt mới.

**Cảnh báo chủ động:** tạo alert với ngưỡng sát giá hiện tại (ví dụ `price_below` = giá hiện tại + 1),
đợi scheduler chạy (mỗi 15 phút, T2–T6 9h–15h giờ VN) → nhận tin nhắn Telegram.

**Bộ nhớ:** restart app, chat tiếp — agent vẫn nhớ hội thoại trước (lưu ở Supabase).

---

## Hai backend LLM — chọn trên web admin

| Backend | Xác thực | Chi phí | Ghi chú |
|---|---|---|---|
| **`subscription`** (mặc định) | `CLAUDE_CODE_OAUTH_TOKEN` | **0đ** — dùng quota gói Claude Pro/Max | Qua Claude Agent SDK. Token hạn 1 năm |
| `api_key` | `CLAUDE_API_KEY` | Tính theo token (~$4–6/tháng) | Qua Messages API |

Cả hai dùng **chung 10 tool**, nên đổi qua lại không thay đổi khả năng của agent. Đổi ở
trang **Cấu hình** trên web admin.

### Lấy token cho backend `subscription`

Chạy trên máy có browser (bạn sẽ đăng nhập và duyệt quyền):

```bash
./scripts/setup_token.sh
```

Token in ra terminal — dán vào `CLAUDE_CODE_OAUTH_TOKEN` trong `.env`. Script dùng binary
Claude Code đi kèm package `claude-agent-sdk`, **không cần cài Node.js**.

Cần gói Claude **Pro, Max, Team hoặc Enterprise**.

### Điều cần biết khi dùng `subscription`

- **Quota dùng chung với Claude Code của bạn.** Bot tiêu cùng hạn mức gói Max. Nếu bot dùng
  nhiều, Claude Code của bạn có thể bị throttle.
- **Token hết hạn sau 1 năm** — chạy lại `./scripts/setup_token.sh` và cập nhật env var.
- **Chậm hơn `api_key`**: Agent SDK spawn một process con cho mỗi tin nhắn.
- **Agent không có quyền shell/file.** Toàn bộ built-in tool (Bash/Read/Write/Edit/WebSearch)
  đã bị tắt bằng `tools=[]`; agent chỉ gọi được 10 tool trong [app/agent/tools.py](app/agent/tools.py).
- **Lịch sử hội thoại vẫn lưu ở Supabase**, không dùng session trên đĩa của SDK — vì
  filesystem trên Railway là ephemeral, redeploy là mất.

## Chi phí & chọn model (chỉ áp dụng cho backend `api_key`)

Model đổi được trên web admin (trang **Cấu hình**), không cần sửa code. Ước tính cho
~10 tin nhắn/ngày:

| Model | Chi phí/tháng | Ghi chú |
|---|---|---|
| `claude-haiku-4-5` | ~2–3 USD | Rẻ nhất, nhưng yếu hơn ở tool-use nhiều bước. **Không** đạt ngưỡng prompt caching (cần prefix ≥ 4096 token, app này ~1050) |
| `claude-sonnet-5` | ~4–6 USD | **Mặc định.** Cân bằng tốt nhất cho phân tích tài chính |
| `claude-opus-5` | ~15–25 USD | Mạnh nhất, dùng khi cần phân tích sâu |

Prompt caching đã bật (breakpoint ở cuối system prompt, cache cả tool schemas). Cache TTL
5 phút nên nó giúp **trong một lượt chat** (2–3 lần gọi API liên tiếp khi agent gọi tool),
không giúp giữa các tin nhắn cách nhau vài giờ.

Mỗi lượt chat log ra số token thực tế — theo dõi bằng:

```bash
docker compose logs -f agent | grep Token
```

Nếu thấy `cache_read=0` liên tục trong cùng một lượt chat, prefix đã tụt xuống dưới ngưỡng
tối thiểu của model (thường do system prompt bị rút ngắn quá nhiều).

## Mở rộng sau này

**Thêm nguồn dữ liệu / broker API (SSI FastConnect, DNSE, VNDirect):** viết module mới trong
`app/tools/`, thêm schema vào `TOOL_SCHEMAS` và một nhánh trong `_dispatch` ở
[app/agent/tools.py](app/agent/tools.py). Không cần sửa orchestrator.

**Key của broker:** bảng `secrets` trong Supabase đã có sẵn; mã hoá bằng Fernet (`FERNET_KEY`)
trước khi lưu, không bao giờ lưu plaintext.

**Đặt lệnh giao dịch thật:** hiện ngoài phạm vi. Nếu làm, nên yêu cầu xác nhận thủ công qua
Telegram inline button trước mỗi lệnh và log đầy đủ.

---

## Deploy

Xem [DEPLOY.md](DEPLOY.md) — Railway (nhanh nhất) hoặc VPS.

App cần **1 process chạy liên tục 24/7** (Telegram polling + scheduler), nên **không deploy
được lên Vercel/Netlify/Cloudflare Workers** — các nền tảng serverless không có process sống
liên tục. Chi tiết ở đầu DEPLOY.md.
