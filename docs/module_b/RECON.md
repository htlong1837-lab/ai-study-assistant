# Báo cáo Khảo sát Repo (Reconnaissance) — Module B

**Ngày khảo sát**: 2026-11-08  
**Người thực hiện**: Module B (Trường)  
**Mục đích**: Xác minh toàn bộ các giả định kỹ thuật giữa tài liệu thiết kế và mã nguồn thực tế trong `core/`.

---

## 1. Bảng đối chiếu giả định kỹ thuật

| Thành phần khảo sát | Giả định ban đầu | Thực tế trong mã nguồn (`core/`) | Đánh giá & Giải pháp |
|---|---|---|---|
| **`ClassifiedEmail`** | Có `id, label, body, attachments, safety_status, received_at, can_forward()` | `id: str`, `sender: str`, `subject: str`, `body: str`, `received_at: datetime`, `label: EmailLabel`, `safety: SafetyStatus`, `summary: str \| None`, `attachments: list[str]`, `label_confidence: float` | ✅ **Khớp**. Thuộc tính an toàn tên là `safety` (Enum `SafetyStatus`). Hàm `can_forward(email)` có sẵn trong `core/contracts.py`. |
| **`ParsedDocument`** | `doc_id`, `pages: list[Page(number, text)]` | `doc_id: str`, `filename: str`, `pages: list[Page(number: int, text: str)]`. Có sẵn phương thức `text_of(numbers)`. | ✅ **Khớp hoàn toàn**. |
| **`Task`** | `id, title, course, deadline, estimated_hours, priority, source, confidence, status` | `id: str`, `title: str`, `course: str`, `deadline: datetime`, `estimated_hours: float`, `priority: Priority`, `source: str`, `confidence: float`, `status: TaskStatus` | ⚠️ **Lưu ý**: `contracts.Task` bắt buộc `deadline` phải là kiểu `datetime` (không cho phép `None`). Khi trích xuất đề xuất chưa tìm thấy hạn nộp, Module B lưu nội bộ trong bảng `tasks` (`deadline IS NULL`) và chỉ chuyển sang `contracts.Task` khi sinh viên đã bổ sung hạn nộp. |
| **Các Enums** | `Priority`, `TaskStatus`, `SafetyStatus` | `Priority(LOW="low", MEDIUM="medium", HIGH="high")`<br>`TaskStatus(PROPOSED="proposed", CONFIRMED="confirmed", CANCELLED="cancelled")`<br>`SafetyStatus(SAFE="safe", SUSPICIOUS="suspicious", MALICIOUS="malicious")` | ✅ **Khớp hoàn toàn**. |
| **Múi giờ của `received_at`** | Có timezone (`tz-aware`) | Trong `core/mocks.py`, `BASE_TIME = datetime(2026, 11, 9, 8, 0)` là datetime naive. | 💡 **Giải pháp**: Động cơ chuẩn hóa thời gian `datetime_normalizer.py` hỗ trợ linh hoạt cả datetime naive và tz-aware, mặc định quy chuẩn về `Asia/Ho_Chi_Minh` (+07:00). |
| **Email `thread_id` / `In-Reply-To`** | Dùng để khớp email dời hạn với task cũ | Trong `ClassifiedEmail` hiện chưa có trường `thread_id` hoặc `in_reply_to`. | 💡 **Giải pháp**: Tạm thời so khớp thông qua tiêu đề, trường `refers_to` và tên môn học; đồng thời ghi nhận đề xuất vào `CONTRACT_REQUESTS.md`. |
| **`core/llm_client.py`** | Structured output, cache, đếm token | `LLMClient` hỗ trợ hàm `generate(prompt, system, temperature)` trả về `LLMResponse(text, input_tokens, output_tokens, cached)`. Providers: `"fake"`, `"gemini"`. Lưu cache tại `.cache/llm/`. | ✅ **Khớp**. Module B tự bọc schema validation (Pydantic) và retry 1 lần khi parse JSON từ `LLMResponse.text`. |
| **`core/mocks.py`** | Dữ liệu giả cho email và tài liệu | Có sẵn `emails()` (4 emails gồm SAFE, SUSPICIOUS, MALICIOUS), `documents()` (3 tài liệu), `tasks()` (4 tasks). | ✅ **Khớp hoàn toàn**. |
| **Môi trường Python & Thư viện** | Python ≥ 3.10, Pydantic v2 | Python 3.14, Pydantic 2.14, PyYAML 6.0, pytest 9.2, python-dotenv 1.2. | ✅ **Đã cài đặt đầy đủ và sẵn sàng**. |
| **Vị trí thư mục code** | `modules/b_extraction/` vs `modules/extraction/` | Thư mục `modules/extraction/` đã có sẵn trong repo và được `views/extraction.py` import. | ✅ **Chọn `modules/extraction/`** để tuân thủ quy tắc "Code trong repo thắng". |

---

## 2. Kết luận khảo sát

Toàn bộ các giả định trong kế hoạch thiết kế đều tương thích tốt với mã nguồn hiện tại của nhóm. Không có xung đột phá vỡ (breaking change) nào xảy ra. Module B có thể tiến hành cài đặt Phase 1 và Phase 2 mà không cần sửa bất kỳ file nào trong `core/`.
