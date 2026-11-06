# Contract: `core.llm_client`

```python
from core.llm_client import get_client, LLMNotConfigured, LLMResponse

client = get_client()                 # đọc LLM_PROVIDER, LLM_MODEL, GEMINI_API_KEY từ .env
client.is_configured() -> bool        # False khi thiếu khóa hoặc thiếu thư viện

resp: LLMResponse = client.generate(
    prompt: str,
    *, system: str | None = None,
    temperature: float = 0.0,
    use_cache: bool = True,
)
resp.text: str
resp.cached: bool
resp.input_tokens: int
resp.output_tokens: int

client.usage() -> dict  # {"calls": int, "cache_hits": int, "input_tokens": int, "output_tokens": int}
```

## Hành vi

- Thiếu khóa/thư viện → `generate` ném `LLMNotConfigured` (không ném lỗi khác); trang hiển thị
  cảnh báo, ứng dụng không dừng.
- Cùng (provider, model, system, prompt, temperature) → lần sau trả `cached=True`, không tăng
  `calls` / token, chỉ tăng `cache_hits`.
- File cache hỏng → bỏ qua và gọi lại.
- `LLM_PROVIDER=fake` → trả `"[fake] " + prompt[:80]`, đếm token theo số từ; dùng trong test.

## Mở rộng

Thêm provider: viết hàm `_call_<name>(model, system, prompt, temperature) -> (text, in_tok, out_tok)`
và đăng ký vào `PROVIDERS`. Gửi PDF, structured output: module A/B mở rộng qua spec riêng.
