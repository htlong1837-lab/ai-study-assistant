# Verification log — Module A

## 2026-11-10

- `core/llm_client.py`: `LLMClient` nhận `api_key` tùy chọn ở constructor; `get_client()` vẫn đọc cấu hình cũ, không cần đổi contract cho module khác.
- QA view tạo client theo phiên, không giữ client toàn cục.
- `app.py` đăng ký `views/qa.py` qua `st.Page`; app chung đã có sẵn.
- `ParsedDocument` và `Page` nằm ở `core/contracts.py`; giữ nguyên model dùng chung.
- `core.llm_client` có cache file dùng chung; QA gọi `use_cache=False`, rồi cache chỉ answer `verified` trong `st.session_state` riêng của phiên. Structured QA logs không ghi nội dung prompt/tài liệu.
- Repo có `src/` legacy; code mới không import từ đó. Chưa xóa `src/` vì ngoài phạm vi và có thể còn được nhánh/PR khác dùng.
- Local `origin/main` là ancestor của nhánh hiện tại; chưa xác minh remote CI, mở app bằng trình duyệt hoặc review của Long. Test tự động cục bộ cập nhật 2026-11-11: 206 passed, 1 skipped; QA coverage 86.94%; Ruff pass. AppTest cho app, QA view và xóa key khi rời Reader pass. Test JS được skip do môi trường thiếu Node.
