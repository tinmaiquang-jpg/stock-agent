# Deploy

Chỉ deploy **sau khi đã chạy ổn ở local**. Supabase vẫn ở cloud — chỗ deploy chỉ chạy app.

## Chọn nền tảng

App này là **1 process chạy liên tục 24/7** (Telegram polling + scheduler + web admin).
Điều đó loại trừ các nền tảng serverless:

| Nền tảng | Dùng được? | Lý do |
|---|---|---|
| **Railway / Render / Fly.io** | ✅ Khuyến nghị | Chạy container liên tục, deploy trực tiếp từ Dockerfile có sẵn |
| **VPS** (Vultr, DigitalOcean...) | ✅ | Toàn quyền, rẻ nhất về lâu dài |
| **Vercel / Netlify / Cloudflare Workers** | ❌ | Serverless — không có process chạy liên tục, Telegram polling và APScheduler không hoạt động. Muốn dùng phải viết lại sang webhook + cron, và cron gói free chỉ chạy 1 lần/ngày (không đủ cho cảnh báo giá) |

- **Railway** — nhanh nhất để bắt đầu → [Phần A](#phần-a--deploy-lên-railway-khuyến-nghị)
- **VPS** — kiểm soát tối đa, rẻ nhất khi chạy lâu → [Phần B](#phần-b--deploy-lên-vps)

---

# Phần A — Deploy lên Railway (khuyến nghị)

Railway đọc `Dockerfile` có sẵn, tự build và chạy. Không cần sửa code.

## A1. Đưa code lên GitHub

Repo git đã được khởi tạo sẵn với 1 commit. `.env` **không** nằm trong repo (đã bị `.gitignore`
chặn) — biến môi trường sẽ khai báo trên dashboard Railway.

Tạo repo mới (để **Private** vì đây là project cá nhân) tại https://github.com/new — đừng
tick thêm README/gitignore. Rồi chạy:

```bash
git remote add origin https://github.com/<tên-github-của-bạn>/<tên-repo>.git
git push -u origin main
```

## A2. Tạo service trên Railway

1. Vào https://railway.com → đăng nhập bằng GitHub
2. **New Project** → **Deploy from GitHub repo** → chọn repo vừa push
3. Railway tự phát hiện `Dockerfile` và bắt đầu build (lần đầu ~3–5 phút)

## A3. Khai báo biến môi trường

Mở service → tab **Variables** → **Raw Editor**, dán vào (điền giá trị thật, lấy từ `.env` ở local):

```
CLAUDE_API_KEY=
CLAUDE_MODEL=claude-sonnet-5
TELEGRAM_BOT_TOKEN=
TELEGRAM_OWNER_ID=
SUPABASE_URL=
SUPABASE_KEY=
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=
APP_SECRET_KEY=
TZ=Asia/Ho_Chi_Minh
```

Hai lưu ý:

- `TZ=Asia/Ho_Chi_Minh` là **bắt buộc** — scheduler dựa vào giờ giao dịch VN (T2–T6, 9h–15h).
- Sinh `APP_SECRET_KEY` **mới** cho production, đừng dùng lại key của môi trường dev:
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

Railway tự redeploy sau khi lưu biến.

## A4. Mở web admin ra internet

Tab **Settings** → mục **Networking** → **Generate Domain**. Railway cấp domain dạng
`<tên>.up.railway.app` kèm HTTPS sẵn.

Railway tự inject biến `PORT` và Dockerfile đã dùng `${PORT:-8000}` nên không cần cấu hình
port thủ công. Nếu Railway vẫn hỏi, điền **8000**.

Telegram bot chạy polling nên hoạt động ngay, **không cần** domain.

## A5. Kiểm tra

Tab **Deployments** → **View Logs**. Dấu hiệu chạy đúng:

```
INFO app.main: Telegram bot (polling) va scheduler da chay
```

Rồi:
- Mở domain vừa tạo → đăng nhập web admin
- Nhắn tin cho bot trên Telegram → phải có phản hồi
- Theo dõi chi phí token: lọc log bằng từ khoá `Token`

## A6. Cập nhật về sau

Railway tự deploy lại mỗi khi bạn push lên `main`:

```bash
git add -A && git commit -m "mô tả thay đổi" && git push
```

## Chi phí Railway

Trial cho ~5 USD credit dùng thử. Sau đó gói **Hobby 5 USD/tháng** (đã gồm 5 USD usage —
app này nhẹ nên thường nằm trong hạn mức đó).

> **Render / Fly.io** làm tương tự: trỏ vào repo, dùng Dockerfile, khai báo cùng bộ biến môi
> trường. Với Render chọn loại **Web Service** (không phải Static Site) và **tránh gói Free** —
> gói Free bị sleep khi không có traffic, làm bot chết và scheduler không chạy.

---

# Phần B — Deploy lên VPS

## B1. Chọn VPS

Cấu hình tối thiểu là đủ: **1 vCPU, 1 GB RAM, 20 GB SSD**. App nhẹ (1 process Python),
tải chủ yếu là gọi API ra ngoài.

Gợi ý nhà cung cấp, ưu tiên vị trí gần Việt Nam để latency thấp khi gọi vnstock:

| Nhà cung cấp | Vị trí gần VN | Giá tham khảo |
|---|---|---|
| Vultr | Singapore, Tokyo | ~5–6 USD/tháng |
| DigitalOcean | Singapore | ~6 USD/tháng |
| Hetzner | Singapore | ~5 USD/tháng |
| VNG Cloud / Viettel IDC / BizFly | Việt Nam | ~100–200k VND/tháng |

Chọn OS **Ubuntu 24.04 LTS**.

## B2. Chuẩn bị VPS

SSH vào VPS rồi chạy:

```bash
sudo apt update && sudo apt upgrade -y
```

Cài Docker (script chính thức của Docker):

```bash
curl -fsSL https://get.docker.com | sudo sh
```

Cho user hiện tại dùng docker không cần sudo (đăng xuất/đăng nhập lại sau lệnh này):

```bash
sudo usermod -aG docker $USER
```

Bật firewall, chỉ mở SSH + HTTP + HTTPS:

```bash
sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable
```

## B3. Đưa code lên VPS

Nếu đã push code lên Git (nhớ **không** commit `.env`):

```bash
git clone <repo-url> stock-agent && cd stock-agent
```

Hoặc copy trực tiếp từ máy local (chạy trên máy local):

```bash
rsync -av --exclude .venv --exclude .env --exclude __pycache__ "./" user@vps-ip:~/stock-agent/
```

## B4. Cấu hình

Tạo `.env` trên VPS với đúng các biến như ở local (xem README bước 3). Không dùng lại
`APP_SECRET_KEY` của môi trường dev — sinh key mới:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Sửa domain trong `Caddyfile`: thay `domain.example.com` bằng domain thật đã trỏ **A record**
về IP của VPS.

## B5. Chạy

```bash
docker compose up -d --build
```

Kiểm tra log:

```bash
docker compose logs -f agent
```

Web admin sẽ có tại `https://domain-cua-ban` (Caddy tự lo HTTPS).
Telegram bot chạy ở polling mode nên hoạt động ngay, không cần cấu hình gì thêm.

## B6. Vận hành

```bash
docker compose restart agent      # restart app
docker compose logs --tail 100 agent   # xem log gần nhất
docker compose down               # dừng
docker compose up -d --build      # cập nhật sau khi sửa code
```

`restart: unless-stopped` trong `docker-compose.yml` đảm bảo app tự khởi động lại khi VPS reboot
hoặc app crash.

## B7. (Tuỳ chọn) Chuyển Telegram sang webhook mode

Polling hoạt động tốt cho quy mô cá nhân — chỉ chuyển sang webhook nếu muốn giảm số request
định kỳ ra Telegram API. Cần domain + HTTPS (đã có từ bước B5). Việc này đòi thay đổi
[app/main.py](app/main.py): thay `updater.start_polling()` bằng `bot.set_webhook(url=...)` và
thêm một route `POST /telegram/webhook` nhận update. Chưa làm sẵn vì polling đơn giản hơn và
không có nhược điểm đáng kể ở quy mô này.

## Bảo mật cần lưu ý

- `.env` chứa Claude API key, Supabase service_role key, Telegram token — **không bao giờ
  commit lên Git** (`.gitignore` đã chặn). Trên Railway/Render thì khai báo ở tab Variables;
  trên VPS thì tạo file `.env` trực tiếp trên server.
- Nếu dùng GitHub, để repo ở chế độ **Private**.
- Web admin chỉ có 1 tài khoản, bảo vệ bằng password hash + session cookie. Dùng mật khẩu mạnh.
- Bot Telegram chỉ trả lời `TELEGRAM_OWNER_ID`; người khác nhắn sẽ bị từ chối.
- Nếu key bị lộ: rotate ngay ở Anthropic Console / Supabase / BotFather, rồi cập nhật `.env`
  và `docker compose restart agent`.
