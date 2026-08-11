# Deploy lên VPS

Chỉ làm bước này **sau khi đã chạy ổn ở local**. Supabase vẫn ở cloud — VPS chỉ chạy app.

## 1. Chọn VPS

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

## 2. Chuẩn bị VPS

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

## 3. Đưa code lên VPS

Nếu đã push code lên Git (nhớ **không** commit `.env`):

```bash
git clone <repo-url> stock-agent && cd stock-agent
```

Hoặc copy trực tiếp từ máy local (chạy trên máy local):

```bash
rsync -av --exclude .venv --exclude .env --exclude __pycache__ "./" user@vps-ip:~/stock-agent/
```

## 4. Cấu hình

Tạo `.env` trên VPS với đúng các biến như ở local (xem README bước 3). Không dùng lại
`APP_SECRET_KEY` của môi trường dev — sinh key mới:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Sửa domain trong `Caddyfile`: thay `domain.example.com` bằng domain thật đã trỏ **A record**
về IP của VPS.

## 5. Chạy

```bash
docker compose up -d --build
```

Kiểm tra log:

```bash
docker compose logs -f agent
```

Web admin sẽ có tại `https://domain-cua-ban` (Caddy tự lo HTTPS).
Telegram bot chạy ở polling mode nên hoạt động ngay, không cần cấu hình gì thêm.

## 6. Vận hành

```bash
docker compose restart agent      # restart app
docker compose logs --tail 100 agent   # xem log gần nhất
docker compose down               # dừng
docker compose up -d --build      # cập nhật sau khi sửa code
```

`restart: unless-stopped` trong `docker-compose.yml` đảm bảo app tự khởi động lại khi VPS reboot
hoặc app crash.

## 7. (Tuỳ chọn) Chuyển Telegram sang webhook mode

Polling hoạt động tốt cho quy mô cá nhân — chỉ chuyển sang webhook nếu muốn giảm số request
định kỳ ra Telegram API. Cần domain + HTTPS (đã có từ bước 5). Việc này đòi thay đổi
[app/main.py](app/main.py): thay `updater.start_polling()` bằng `bot.set_webhook(url=...)` và
thêm một route `POST /telegram/webhook` nhận update. Chưa làm sẵn vì polling đơn giản hơn và
không có nhược điểm đáng kể ở quy mô này.

## Bảo mật cần lưu ý

- `.env` chứa Claude API key, Supabase service_role key, Telegram token — chỉ để trên VPS,
  không commit lên Git (`.gitignore` đã chặn).
- Web admin chỉ có 1 tài khoản, bảo vệ bằng password hash + session cookie. Dùng mật khẩu mạnh.
- Bot Telegram chỉ trả lời `TELEGRAM_OWNER_ID`; người khác nhắn sẽ bị từ chối.
- Nếu key bị lộ: rotate ngay ở Anthropic Console / Supabase / BotFather, rồi cập nhật `.env`
  và `docker compose restart agent`.
