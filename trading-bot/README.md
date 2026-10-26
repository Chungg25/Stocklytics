# Stocklytics Trading Bot (Hermes + Telegram)

Module độc lập, không import gì từ `backend/` hay `frontend/`. Người dùng chat với bot Telegram riêng của họ bằng **tiếng Anh**:

1. Mô tả chiến lược.
2. Nhận kết quả backtest kèm biểu đồ.
3. Bật theo dõi để được **thông báo** khi điều kiện thỏa.

Hệ thống **không bao giờ đặt lệnh**: MCP server không có công cụ nào liên quan đến lệnh hay broker.

## Trải nghiệm người dùng (không cần biết kỹ thuật)

1. Mở trang `https://<PUBLIC_BASE_URL>/connect` và quét QR, Telegram mở manager bot → bấm **Start**.
2. Bấm **Create my bot** → màn hình tạo bot của Telegram đã điền sẵn tên → bấm **Create**.
3. Bấm **Open ChatGPT sign-in**, đăng nhập ChatGPT, dán mã. Có sẵn nút **Copy code**.
4. Bấm **Open @bot-của-bạn** và chat, ví dụ:
   > Alert me when AAPL or MSFT RSI crosses above 30 while the price is above the 200-day average; sell when RSI goes above 70, stop-loss 7%.

Bot sẽ:
- đọc lại chiến lược cho người dùng xác nhận;
- backtest, mặc định 3 năm;
- gửi biểu đồ và giải thích kết quả, kể cả điểm yếu;
- hỏi có muốn bật theo dõi không.

Quản lý bằng lời nói tự nhiên: "my strategies", "pause …", "edit …", "how is it doing?", "anything triggering now?".

## Kiến trúc

```
QR → @ManagerBot ──managed_bot──► Provisioner ──► Hermes container (1/người dùng)
                                                    • Telegram gateway = bot riêng của user
                                                    • ChatGPT (openai-codex OAuth)
                                                    • skill stocklytics-trading
                                                    • MCP ──► /mcp (API key riêng)
stockbot (FastAPI)
  strategy/  DSL JSON có whitelist + chỉ báo pandas + bộ đánh giá vector hoá
  backtest/  mô phỏng tất định + metrics + biểu đồ
  data/      yfinance (nến ngày đã chốt) + Finnhub (giá live có timestamp)
  alerts/    kiểm tra mỗi 30' + chốt phiên, gửi thẳng Bot API (không qua LLM)
  store/     SQLAlchemy (Postgres/Supabase hoặc SQLite)
```

- **LLM chỉ dịch và giải thích.** Backtest và kiểm tra tín hiệu là code tất định. Không có `exec` code do LLM sinh ra.
- **Backtest và cảnh báo dùng chung một bộ đánh giá** (`strategy/engine.py`), nên cảnh báo thật khớp với cách backtest vào lệnh.

## Đảm bảo giá đúng thời điểm

| Lúc | Nguồn giá | Quy tắc |
|---|---|---|
| Trong phiên (mỗi 30', 9:30–15:30 ET) | Finnhub `/quote`: giá khớp cuối và **timestamp của sàn** | Bỏ qua nếu giá cũ hơn `MAX_QUOTE_AGE_SECONDS` (mặc định 300s) hoặc không phải phiên hôm nay. Không bao giờ đoán giá. |
| Sau đóng cửa (16:35 và 17:35 ET) | **Giá đóng cửa chính thức**, tức nến ngày đã chốt | Xác nhận tín hiệu trong phiên, hoặc gửi "Signal cancelled". Không dùng giá giao dịch ngoài giờ. |
| Ngày lễ, nghỉ | Finnhub `market-status` | Không chạy. |

Thêm vào đó:
- Mỗi cảnh báo ghi giá, giờ khớp (ET) và nguồn.
- Mỗi tổ hợp (chiến lược, mã, loại, phiên) chỉ báo **một lần**.
- Mọi lần kiểm tra đều được ghi vào `sb_check_runs`, kèm danh sách mã bị loại vì giá cũ.

Trong phiên, nến hôm nay chưa có khối lượng, vì `/quote` không trả về volume. Điều kiện dựa trên khối lượng chỉ được tính ở lần kiểm tra lúc đóng cửa.

## Cài đặt (vận hành)

1. **Manager bot:**
   - Tạo bot bằng @BotFather.
   - Bật **Bot Management** (Managed Bots, Bot API 9.6) trong BotFather.
   - Đặt `MANAGER_BOT_TOKEN` và `MANAGER_BOT_USERNAME`.
2. **Finnhub:** đăng ký key miễn phí và đặt `FINNHUB_API_KEY`.
3. `cp .env.example .env` rồi điền các giá trị:
   - `PUBLIC_BASE_URL` phải là HTTPS;
   - `TELEGRAM_WEBHOOK_SECRET`;
   - `TOKEN_ENCRYPTION_KEY`;
   - `DATABASE_URL`.
4. **Build image Hermes** (có sẵn skill): `docker build -t stocklytics/hermes-trader:latest hermes`. Nên pin `HERMES_VERSION`.
5. **Chạy:** `mkdir -p /var/lib/stockbot/hermes && docker compose up -d --build`. Webhook của manager bot tự đăng ký khi khởi động.
6. Gửi link `https://<PUBLIC_BASE_URL>/connect` (hoặc in QR) cho người dùng.

## Kiểm thử

```bash
pip install -r requirements.txt pytest
python -m pytest -q tests
```

Các kiểm thử chạy offline:
- chỉ báo và crossover;
- validate DSL;
- khớp lệnh ở giá mở cửa phiên sau (không nhìn trước tương lai);
- cắt lỗ khi giá mở cửa nhảy qua mức cắt lỗ, chốt lời;
- cảnh báo: chỉ báo một lần, loại giá cũ, hủy tín hiệu cuối phiên, chờ giá đóng cửa chính thức;
- luồng onboarding (Telegram và Docker giả);
- MCP từ chối khi thiếu API key.

## Giới hạn và việc cần xác minh khi triển khai

- **Managed Bots** (`t.me/newbot/...`, update `managed_bot`, `getManagedBotToken`) là API mới của Telegram. Cần thử với tài khoản thật.
- **Đăng nhập ChatGPT** dùng luồng mã thiết bị của Hermes (`hermes auth add openai-codex`). Code bắt URL và mã từ output của lệnh này. Nếu Hermes đổi định dạng output, sửa `URL_RE`/`CODE_RE` trong `bot/provisioner.py`.
- **Finnhub gói free:** 60 lần gọi/phút. Với khoảng 55 mã mỗi phút, một lượt kiểm tra nhiều mã sẽ kéo dài vài phút, nhưng mỗi mã vẫn ghi đúng giờ giá của nó.
- **Mỗi người dùng một container Hermes**, mặc định giới hạn 768 MB RAM và 0.5 CPU.
