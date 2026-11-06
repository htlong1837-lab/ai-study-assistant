# Research: Khung dự án

## R1. Điều hướng nhiều trang trong Streamlit

- **Decision**: `st.navigation([st.Page(...)])` trong `app.py`, trang đặt trong `views/`.
- **Rationale**: Gom tiêu đề, icon, nhóm trang ở một chỗ; tránh cơ chế thư mục `pages/` tự động
  (khó đặt tên tiếng Việt và thứ tự).
- **Alternatives**: Thư mục `pages/` tự động (bị loại vì kém kiểm soát); một trang với
  `st.tabs` (bị loại vì 4 người sửa chung một file dễ xung đột merge).

## R2. Kiểu hợp đồng dữ liệu

- **Decision**: `dataclass` chuẩn + `__post_init__` kiểm tra hợp lệ, enum kế thừa `str`.
- **Rationale**: Kế hoạch nhóm ghi "Python dataclass"; không thêm thư viện; enum `str` lưu
  thẳng vào SQLite/JSON được.
- **Alternatives**: pydantic (mạnh hơn nhưng thêm một khái niệm cả nhóm phải học; LLM SDK
  module B dùng có thể vẫn cần pydantic cho structured output — B tự quyết trong spec của mình).

## R3. Nhà cung cấp LLM và cách gọi

- **Decision**: `LLMClient` với provider cắm được; cài sẵn `gemini` (thư viện `google-genai`,
  import lười) và `fake` (trả lời cố định, dùng cho test). Thêm provider khác = thêm một hàm.
- **Rationale**: Gemini có hạn mức miễn phí, nhận PDF và structured output (module A, B cần).
  Import lười giúp ứng dụng chạy khi chưa cài hoặc chưa có khóa.
- **Alternatives**: Dify (đã loại — thêm dịch vụ phải tự host, xem nhật ký quyết định ngày
  2026-11-06); LiteLLM (thêm phụ thuộc lớn, chưa cần).

## R4. Cache và đếm chi phí

- **Decision**: Khóa cache = SHA-256 của (provider, model, system, prompt, tham số); mỗi kết quả
  một file JSON trong `.cache/llm/`; thống kê dồn vào `.cache/llm/usage.json`.
- **Rationale**: Không cần thư viện; xoá thư mục là reset; file hỏng thì bỏ qua và gọi lại.
- **Alternatives**: SQLite (thừa cho nhu cầu này), `functools.lru_cache` (mất khi khởi động lại).

## R5. Kiểm thử trang

- **Decision**: `streamlit.testing.v1.AppTest.from_file(...)` chạy từng file trong `views/`,
  khẳng định không có exception.
- **Rationale**: Bắt lỗi import/hiển thị mà không mở trình duyệt; chạy offline.
