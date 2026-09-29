# chatbot-core

Core chatbot dạng "Plug & Play": tool được nhúng trực tiếp vào process (không qua MCP server riêng), mỗi tool tự khai báo "thông số" qua file `tool.yaml` cạnh nó.

## Kiến trúc

```
User -> AgentCore (SessionStore theo session_id) -> LLM (OpenAI, tool_choice=auto)
                   -> nếu LLM yêu cầu gọi tool:
                        - tool có requires_confirmation=true?
                            -> dừng lại, hỏi user xác nhận (có/không) trước
                        - validate arguments theo JSON Schema của tool.yaml
                        - chạy các tool_calls trong cùng 1 lượt SONG SONG (asyncio.gather)
                        - await asyncio.wait_for(tool.execute(**args), timeout)
                        - trả kết quả (string) về cho LLM
                   -> lặp tối đa MAX_TOOL_ITERATIONS vòng, LLM tổng hợp -> trả lời user
```

- `core/base_tool.py` — chuẩn giao tiếp (`BaseTool`). Không hardcode name/description/parameters trong code; tất cả đọc từ `config` (tool.yaml) truyền vào lúc khởi tạo, kể cả cờ `requires_confirmation`.
- `core/registry.py` — BIOS: quét `tools/*/`, với mỗi thư mục có đủ `tool.yaml` + `tool.py` thì đọc yaml, import class kế thừa `BaseTool`, khởi tạo và đăng ký. Trước khi thực thi, validate `arguments` từ LLM theo JSON Schema (`tool.parameters`) bằng `jsonschema` — sai schema thì trả lỗi rõ ràng cho LLM tự sửa, không chạy `execute()`. Bọc `execute()` trong `try/except` + `asyncio.wait_for(timeout)` để lỗi/treo của 1 tool không làm sập cả Core.
- `core/llm_client.py` — tạo `AsyncOpenAI` client; đọc `OPENAI_USE_CUSTOM_ENDPOINT`/`OPENAI_CUSTOM_BASE_URL` để quyết định dùng API OpenAI chính thức hay endpoint riêng (self-host/proxy).
- `core/session_store.py` — `SessionStore` lưu lịch sử hội thoại theo `session_id` (in-memory), tự cắt bớt lượt cũ nhất khi vượt `MAX_HISTORY_MESSAGES` (không bao giờ cắt giữa cặp `assistant(tool_calls)` ↔ `tool` response). Cho phép nhiều hội thoại độc lập cùng lúc trong 1 process; khi ghép vào server thật chỉ cần thay class này bằng bản Redis/DB cùng API.
- `core/agent.py` — vòng lặp điều phối: gọi LLM kèm schema tool (bọc try/except, lỗi mạng/API không làm sập Core) -> nếu có `tool_calls` thì kiểm tra tool nào cần xác nhận, chạy các tool còn lại song song qua registry -> gửi kết quả lại cho LLM -> lặp đến khi LLM trả lời text cuối cùng hoặc chạm `MAX_TOOL_ITERATIONS`.
- `tools/<tên_tool>/tool.yaml` — "thông số ổ cứng": `name`, `description`, `parameters` (JSON Schema), `timeout`, `requires_confirmation` (tùy chọn, mặc định `false`).
- `tools/<tên_tool>/tool.py` — logic thực thi (hộp đen), chỉ cần implement `async def execute(self, **kwargs)`.

Kèm sẵn 3 tool demo (`payment_tool`, `order_tool`, `hello`) — không có logic thật, chỉ `sleep` rồi trả về chuỗi hardcode, để minh họa luồng nhúng tool. `payment_tool` có `requires_confirmation: true` để minh họa guardrail cho thao tác nhạy cảm.

### Biến môi trường bổ sung

- `MAX_TOOL_ITERATIONS` (mặc định `8`) — số vòng gọi tool tối đa trong 1 lượt chat, tránh loop vô hạn.
- `MAX_HISTORY_MESSAGES` (mặc định `30`) — số message tối đa giữ lại mỗi session trước khi bị cắt bớt.

## Cài đặt

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # điền OPENAI_API_KEY (và custom endpoint nếu cần)
python main.py
```

## Chạy với Docker

Xem hướng dẫn chi tiết các lệnh Docker tại [DOCKER.md](DOCKER.md).

```bash
cp .env.example .env
docker compose run --rm chatbot-core
```

## Thêm một tool mới (cắm SSD mới)

1. Tạo thư mục `tools/<tên_tool>/`.
2. Tạo `tool.yaml` khai báo `name`, `description`, `parameters` (JSON Schema chuẩn OpenAI function-calling), `timeout` (tùy chọn), `requires_confirmation: true` nếu đây là thao tác nhạy cảm (thanh toán, xoá dữ liệu...) cần hỏi lại user trước khi chạy.
3. Tạo `tool.py` với 1 class kế thừa `BaseTool`, chỉ cần override `async def execute(self, **kwargs)`.
4. Chạy lại `main.py` — Core tự quét, tự nhận diện, tự gửi schema cho LLM. Không sửa gì trong `core/`.

## Chạy test

```bash
pip install -r requirements-dev.txt
pytest -q
```
