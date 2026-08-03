# Chat Bukkigo

Python backend cho chatbot tư vấn thẩm mỹ nail. Phiên bản này tập trung vào lõi: skill, intent routing, progressive reference loading và OpenAI Responses API. Giao diện nhúng chatbot và RAG/catalogue sẽ được nối sau.

## Cấu trúc

- `skills/nail-beauty-consultant/`: skill và 8 reference thẩm mỹ.
- `src/chat_bukkigo/router.py`: nhận diện intent và kiểu phản hồi (`direct`, `recommend`, `explore`, `compare`, `refine`, `safety`).
- `src/chat_bukkigo/prompt_builder.py`: nạp tối đa hai reference cần thiết và gắn hợp đồng độ dài theo từng lượt.
- `src/chat_bukkigo/service.py`: gọi OpenAI Responses API.
- `config/app.yaml`: cấu hình không nhạy cảm.
- `.env`: API key và secret cục bộ, không commit.

Endpoint được điều khiển bằng `.env`:

```env
OPENAI_USE_CUSTOM_ENDPOINT=false
OPENAI_CUSTOM_BASE_URL=
```

Để dùng 9router cục bộ:

```env
OPENAI_USE_CUSTOM_ENDPOINT=true
OPENAI_CUSTOM_BASE_URL=http://localhost:20128/v1
```

## Chạy local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
# sửa OPENAI_API_KEY trong .env
uvicorn chat_bukkigo.main:app --reload
```

Kiểm tra:

```bash
pytest
ruff check .
```

Mở giao diện chat:

```text
http://127.0.0.1:8000/v1/chat
```

Gọi API JSON:

```bash
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Tư vấn cho tôi một bộ móng đẹp đi chơi Tết, sang nhưng không quá nổi"}'
```

API trả thêm `intent`, `response_mode` và `references_used` để kiểm tra router có nạp đúng ngữ cảnh hay không. Lịch sử hội thoại được client gửi lại trong `history`; lượt user gần nhất được dùng để nhận ra các câu chỉnh tiếp như “nhẹ hơn chút” mà không tư vấn lại từ đầu. Mặc định server không yêu cầu OpenAI lưu response.

Prompt V2 ưu tiên câu trả lời ngắn theo ngữ cảnh thay vì một giới hạn từ cứng. Các case routing và tiêu chí review thủ công nằm trong `evals/`; chạy `pytest` để kiểm tra giới hạn số reference và kích thước context.

Streaming dùng `POST /v1/chat/stream` với response `text/event-stream`. Event `done` trả `time_to_first_token_ms` và `total_ms`; giao diện cũng đo tổng end-to-end từ trình duyệt.

## Logging và bắt lỗi

Log được ghi đồng thời ra console và file xoay vòng `logs/chat-bukkigo.log`.
Mỗi lượt chat có một `trace_id`; khi request lỗi, giao diện hiện mã này để đối
chiếu với log. Hệ thống ghi endpoint, model, intent, TTFT, tổng thời gian, loại
lỗi, HTTP status và request ID của provider, nhưng không ghi API key hoặc nội
dung hội thoại.

```bash
tail -f logs/chat-bukkigo.log
```

Có thể đổi mức và vị trí log trong `.env` bằng `LOG_LEVEL` và `LOG_FILE`.
