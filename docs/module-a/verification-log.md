# Module A Verification Log

Nhật ký đối chiếu mã nguồn thực tế trước và sau khi thực hiện các Task gắn nhãn `[VERIFY]`.

## Bổ sung kiểm tra lịch sử theo review PR — 2026-11-09

- Thay fixture `fake_aiza` trong `tests/unit/test_api_key_lifecycle.py` bằng placeholder không mang hình thức API key.
- Quét các refs Git local bằng tìm kiếm mẫu key, chỉ xuất commit và tên file. Có một commit chứa fixture key-like tại file test này; giá trị không được in ra hoặc lưu trong log.
- Đọc snapshot `src/llm_client.py` của commit đó qua bộ lọc chỉ trả metadata: không có khai báo `DEFAULT_GEMINI_API_KEY` và không có chuỗi khớp mẫu Google `AIza`/`AQ.`. `.env` không nằm trong Git history local.
- **Cập nhật từ người dùng:** `.env` cục bộ trước đây có key thật; hiện hai biến key đã để trống và người dùng xác nhận key cũ đã được xóa/thu hồi trên Google AI Studio. Người dùng không nhớ fixture lịch sử có trùng key thật hay không. Git xác nhận `.env` không nằm trong lịch sử local.
- **Kết luận:** fixture trong test có hình thức giống key; chưa thể kết luận fixture là giả/thật hoặc trùng/khác key cũ. Không rewrite lịch sử khi chưa có căn cứ và thống nhất nhóm. Có thể kiểm tra credentials ở tất cả project liên quan; không khôi phục key chỉ để đối chiếu.
- **Cập nhật cuối từ người dùng:** fixture lịch sử là dữ liệu giả, nhận biết qua chuỗi ký tự tuần tự. Key thật cũ trong `.env` đã được thu hồi. Do `.env` không được track và fixture được xác nhận giả, không có credential thật nào cần rewrite khỏi lịch sử local.
- Lưu ý: các kết luận mạnh hơn trong ghi chú Task 0.1 cũ không được lịch sử Git hiện có xác nhận độc lập; phần bổ sung này là kết quả mới nhất của lần audit.

---

## Task 0.1: Loại bỏ key hardcode và chuyển sang "Người dùng tự nhập API key" `[VERIFY]`

- **Thời điểm xác minh**: 2026-11-08
- **Mô tả nghi vấn ban đầu**: `DEFAULT_GEMINI_API_KEY` bị hardcode trong `src/llm_client.py`; file `.env` chứa key thật nằm ở thư mục gốc.
- **Kết quả đối chiếu code thật**:
  - `src/llm_client.py:17`: Tồn tại dòng `DEFAULT_GEMINI_API_KEY = "[REDACTED]"`. Đúng như mô tả.
  - `.env`: Tồn tại 2 biến `GEMINI_API_KEY` và `GOOGLE_API_KEY` mang giá trị key thật. Đúng như mô tả.
  - Hàm `_ensure_env_file()` tự động tạo và ghi key vào `.env` nếu thiếu.
- **Kết luận xác minh**: **ĐÚNG THỰC TẾ**. Lỗ hổng rò rỉ key là thật và rất nghiêm trọng.
- **Hành động đã xử lý**:
  - Xóa bỏ hằng số `DEFAULT_GEMINI_API_KEY` khỏi `src/llm_client.py`.
  - Bắt buộc tham số `api_key` trong `LLMClient.__init__`. Nếu thiếu ném `MissingAPIKeyError`.
  - Tạo `src/errors.py` và `src/utils/security.py` (`mask_secrets`).
  - Cập nhật UI `streamlit_app.py` với expander hướng dẫn, ô nhập key tùy chọn, badge trạng thái, hỗ trợ default key của host.
  - Dọn dẹp `.env`, tạo `docs/module-a/SECURITY_TODO.md`.

---

## Task 0.3: Sửa `answer_id` không duy nhất `[VERIFY]`

- **Thời điểm xác minh**: 2026-11-08
- **Mô tả nghi vấn ban đầu**: `answer-{doc_id}-{len(pages)}` giống nhau cho mọi câu hỏi trên cùng tài liệu; `question_id` bị gán tĩnh `f"question-{document.doc_id}"`.
- **Kết quả đối chiếu code thật**:
  - `src/qa_service.py:35`: `answer_id=f"answer-{document.doc_id}-{len(document.pages)}"`. Đúng như mô tả! Mọi câu hỏi trên cùng doc đều ra cùng một ID!
  - `src/qa_service.py:37`: `question_id=f"question-{document.doc_id}"`. Đúng như mô tả!
- **Kết luận xác minh**: **ĐÚNG THỰC TẾ**. Gây ra xung đột định danh, phá vỡ hệ thống theo dõi và cache.
- **Hành động đã xử lý**:
  - Đổi `answer_id = f"answer-{document.doc_id}-{uuid4().hex[:12]}"` (đảm bảo tính độc nhất).
  - Đổi `question_id = f"q-{hashlib.sha256(normalised.encode('utf-8')).hexdigest()[:12]}"` với chuẩn hóa Unicode NFC để đảm bảo tính ổn định và tái lập khi cùng một câu hỏi được hỏi lại.

---

## Task 0.4: Chuẩn hóa danh sách model & bảng giá `[VERIFY]`

- **Thời điểm xác minh**: 2026-11-08
- **Mô tả nghi vấn ban đầu**: Tên `gemini-3.8-flash` đáng ngờ (có thể ảo); model 1.5/2.0 có thể đã ngừng; bảng giá hardcode.
- **Kết quả đối chiếu code thật & tra cứu thực tế**:
  - Trong code: `LLMClient` hardcode model mặc định `gemini-3.8-flash` và bảng giá tĩnh `model_prices`.
  - Tra cứu thực tế hệ thống Gemini API: `gemini-3.8-flash` và `gemini-4-argon` thực sự là dòng mô hình thế hệ mới nhất của Google (Gemini 4 & 3.x), không phải tên ảo! Ngược lại, các model 1.5/2.5 đã là thế hệ trước.
  - Tuy nhiên, `gemini-4-argon` đòi hỏi tài khoản có trả phí (Billing), trong khi `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash` có gói Free Tier (miễn phí, không cần thẻ).
- **Kết luận xác minh**: **MÔ TẢ BAN ĐẦU ĐÚNG VỀ HARDCODE, NHƯNG NHẦM VỀ MODEL**.
- **Hành động đã xử lý**:
  - Tạo `config/models.yaml` định nghĩa danh mục đa tầng hoàn chỉnh:
    - Nhóm mô hình mạnh: `gemini-4-argon`, `gemini-3.8-flash`.
    - Nhóm mô hình miễn phí: `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash`.
  - Tạo `src/config.py` đọc file cấu hình và hỗ trợ override bằng biến môi trường `LLM_MODEL_CASCADE`.
  - Bảng giá chính thức được chuẩn hóa theo per 1K tokens.
  - Tạo script CLI `scripts/list_models.py` để tra cứu danh sách model thực tế từ key.
