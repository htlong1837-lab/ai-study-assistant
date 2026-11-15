# Module A Changelog

Tất cả các thay đổi kỹ thuật của Module A được ghi nhận tại đây theo từng Task.

---

## [Reader + QA hardening] - 2026-11-11

- Hoàn thiện backend hỏi theo đoạn/toàn tài liệu, parser/verifier, retrieval BM25, lịch sử luồng và cache verified theo session.
- Tích hợp PDF.js 6.4.299, viewer/chọn đoạn/chat/citation navigation; thêm component wrapper và dev harness.
- Thêm benchmark validator/runner, structured logging và hướng dẫn benchmark; chưa có gold dataset do người dùng xác nhận.
- Bổ sung thread store có ID ổn định, export Markdown có câu hỏi/citation, khớp đoạn qua trang, validation event chặt hơn và dedup đúng một lần trong session.
- Reader có toolbar trang/zoom/theme, popup cạnh vùng chọn, giải phóng canvas ngoài viewport, kiểm tra `event.source` và tắt PDF scripting/eval.
- App xóa API key QA khỏi session state khi điều hướng khỏi trang Reader; citation hỏi toàn tài liệu giờ có nút quay lại đúng trang, mọi rejection hiển thị thông báo tiếng Việt.
- Kiểm chứng cục bộ cập nhật 2026-11-11: 206 passed, 1 skipped; QA coverage 86.94%; Ruff pass. JS test skip vì Node chưa có trên máy này.
- Đã bổ sung timeout/retry Gemini và PDF parser subprocess ở 2026-11-11. Còn cần browser QA, benchmark thật/latency, kiểm thử tích hợp B/D, OCR/crop theo phê duyệt nhóm và review/merge.

---

## [Phase 0] - Khẩn cấp: Bảo mật & Bug thật (2026-11-08)

### fix(A-0.1): Quản lý API Key linh hoạt, hỗ trợ Default Key & Thêm hướng dẫn người dùng
- Xóa bỏ hoàn toàn hằng số `DEFAULT_GEMINI_API_KEY` khỏi `src/llm_client.py`.
- Định nghĩa module ngoại lệ `src/errors.py`: `ModuleAError`, `MissingAPIKeyError`, `InvalidAPIKeyError`, `QuotaExceededError`, `LLMUnavailableError`.
- `LLMClient` yêu cầu `api_key: str` trong `__init__`.
- Tạo `src/utils/security.py` chứa hàm `mask_secrets` che giấu các pattern API key trong log/thông báo lỗi.
- Nâng cấp `src/streamlit_app.py`:
  - Thêm expander hướng dẫn người dùng hiểu rõ API key là gì và cách lấy key miễn phí tại Google AI Studio.
  - Ô nhập API Key cho phép để trống: tự động lấy default key từ môi trường host hoặc Streamlit secrets.
  - Thêm badge hiển thị trạng thái (Key cá nhân vs Key mặc định hệ thống vs Chưa có key).
  - Nút kiểm tra key và nút xóa key.
- Dọn dẹp `.env`, tạo `.env.example`, tạo `docs/module-a/SECURITY_TODO.md` và `tests/test_no_secrets.py`.

### fix(A-0.2): Bỏ `_ensure_env_file()` và mọi thao tác ghi file cấu hình ngầm
- Xóa bỏ `_ensure_env_file()`, `_env_file_path()`, `_load_api_key()` trong `src/llm_client.py`.
- Gỡ bỏ phụ thuộc `python-dotenv` trong `src/`.
- Chuyển `mkdir` của cache directory sang dạng Lazy: chỉ tạo thư mục khi có dữ liệu ghi vào cache (`_write_cache`), khởi tạo `LLMClient` không tạo ra bất kỳ file hay thư mục nào trên đĩa.
- Bổ sung unit test `tests/unit/test_no_side_effects.py`.

### fix(A-0.3): Sửa `answer_id` không duy nhất
- Thay đổi logic sinh `answer_id` trong `src/qa_service.py` từ định dạng tĩnh thành `f"answer-{doc_id}-{uuid4().hex[:12]}"`.
- Chuẩn hóa hàm sinh `question_id` sử dụng Unicode NFC và SHA256 để đảm bảo tính đồng nhất dù người dùng gõ theo kiểu Telex hay VNI.
- Bổ sung unit test `tests/unit/test_id_generation.py`.

### fix(A-0.4): Chuẩn hóa danh mục Model đa tầng & Bảng giá
- Tạo `config/models.yaml` định nghĩa danh mục cả model mạnh (`gemini-4-argon`, `gemini-3.8-flash`) và model miễn phí (`gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash`).
- Tạo `src/config.py` đọc cấu hình, hỗ trợ override biến môi trường `LLM_MODEL_CASCADE` và tính phí theo token thực tế.
- Tích hợp `src/config.py` vào `src/llm_client.py`.
- Tạo công cụ CLI `scripts/list_models.py` cho phép tra cứu model khả dụng trên API key.
- Bổ sung unit test `tests/unit/test_model_config.py`.

### fix(A-0.5): Gắn nhãn câu trả lời từ fallback local & Ngăn ngừa nhiễm độc Cache
- Bổ sung trường `source: Literal["llm", "cache", "local_fallback"]` và `model_used: str | None` vào `Answer` dataclass trong `src/models/answer.py`.
- Đảm bảo tính tương thích ngược trong `Answer.to_dict()` và `Answer.from_dict()`.
- Cập nhật `src/llm_client.py`: Khi đọc cache thành công gán `source = "cache"`; khi gọi LLM thành công gán `source = "llm"`; khi rơi vào keyword fallback gán `source = "local_fallback"` và **TUYỆT ĐỐI KHÔNG GHI VÀO CACHE**.
- Cập nhật `src/streamlit_app.py` hiển thị banner cảnh báo màu vàng khi câu trả lời bắt nguồn từ local fallback.
- Bổ sung unit test `tests/unit/test_fallback_labeling.py`.
