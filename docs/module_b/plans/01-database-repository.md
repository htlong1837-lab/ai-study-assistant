# Sub-Plan 1: Cơ sở dữ liệu SQLite dùng chung & Repository (FR-B06)

> **Mục tiêu:** Xây dựng schema cơ sở dữ liệu SQLite dùng chung cho toàn bộ dự án và lớp truy xuất dữ liệu `Repository` phục vụ lưu trữ tác vụ, trích xuất học vụ, mâu thuẫn và log.  
> **Ước tính thời gian:** 3 giờ  
> **Phase tương ứng:** Phase 1 (Ưu tiên cao - các module khác phụ thuộc)

---

## 1. Thiết kế Schema Cơ sở dữ liệu (`db/schema.sql`)

Cần thiết kế các bảng tuân thủ nguyên tắc toàn vẹn dữ liệu:
- Mọi timestamp lưu dưới dạng ISO-8601 kèm múi giờ (hoặc múi giờ chuẩn +07:00).
- Bật `PRAGMA foreign_keys = ON;` và `PRAGMA journal_mode = WAL;`.
- Bảng chính:
  1. `tasks`: Lưu nhiệm vụ ở cả 3 trạng thái (`proposed`, `confirmed`, `cancelled`). Trường `deadline` cho phép `NULL` khi ở trạng thái `proposed` (để lưu trữ các bài tập chưa phân giải được hạn nộp).
  2. `task_sources`: Quan hệ 1-N lưu vết nguồn gốc trích xuất (`email:<id>`, `doc:<doc_id>#p<n>`), tên trường và đoạn trích dẫn nguyên văn (`quote`).
  3. `assignment_details`: Quan hệ 1-1 với `tasks`, lưu thông tin mở rộng: `raw_deadline_text`, `submission_format` (JSON array), `submission_platform`, `naming_convention`, `grading_criteria` (JSON array), `assumptions` (JSON array).
  4. `conflicts`: Lưu các trường hợp mâu thuẫn (`deadline`, `submission`, `ambiguity`, `outdated`), giá trị và nguồn gốc 2 bên, đề xuất của hệ thống, trạng thái giải quyết (`resolution`, `resolved_at`).
  5. `task_update_proposals`: Lưu đề xuất cập nhật bài tập khi nhận được email dời hạn/thay đổi yêu cầu đối với một task đã tồn tại (kể cả task đã `confirmed`).
  6. `extraction_logs`: Lưu vết lịch sử gọi LLM, token, thời gian chạy và hash nội dung để kiểm tra bộ nhớ đệm (`UNIQUE(source_id, content_hash, prompt_version)`).

---

## 2. Nhiệm vụ chi tiết (Checklist)

- [ ] **T01.1 — Soạn thảo `db/schema.sql`:**
  - Viết đầy đủ câu lệnh `CREATE TABLE IF NOT EXISTS` cho 6 bảng trên.
  - Thiết lập ràng buộc khóa ngoại `ON DELETE CASCADE` hợp lý.
- [ ] **T01.2 — Cài đặt `db/repository.py`:**
  - `init_db(db_path: Path | str)`: Mở kết nối, thực thi `schema.sql`, bật Foreign Keys và WAL mode. Đảm bảo idempotent (gọi nhiều lần không gây lỗi).
  - Kết nối theo yêu cầu: Mở kết nối mới trên mỗi hàm hoặc transaction (phù hợp với chu kỳ chạy của Streamlit), không giữ kết nối toàn cục dạng module-level state.
  - Các hàm CRUD cốt lõi:
    - `create_task(task_data: dict) -> str`
    - `get_task(task_id: str) -> dict | None`
    - `list_tasks(status: str | None = None) -> list[dict]`
    - `update_task_fields(task_id: str, **fields) -> None`
    - `set_task_status(task_id: str, status: str, confirmed_at: str | None = None) -> None`
    - `add_sources(task_id: str, sources: list[dict]) -> None`
    - `save_assignment_details(task_id: str, details: dict) -> None`
    - `get_assignment_details(task_id: str) -> dict | None`
    - `add_conflict(conflict_data: dict) -> int`
    - `resolve_conflict(conflict_id: int, resolution: str, resolved_at: str) -> None`
    - `add_update_proposal(proposal_data: dict) -> int`
    - `list_pending_proposals(task_id: str | None = None) -> list[dict]`
    - `set_update_proposal_status(proposal_id: int, status: str) -> None`
    - `log_extraction(log_data: dict) -> int`
    - `get_cached_extraction(source_id: str, content_hash: str, prompt_version: str) -> dict | None`
- [ ] **T01.3 — Kiểm thử đơn vị `tests/extraction/test_repository.py`:**
  - Test kiểm tra `init_db` idempotent.
  - Test tạo, đọc, cập nhật trạng thái Task và đảm bảo quan hệ Cascade Delete hoạt động (xoá task xoá luôn sources, details, conflicts).
  - Test `deadline = NULL` được chấp nhận cho task `proposed`.
  - Test vi phạm ràng buộc duy nhất trong `extraction_logs` khi trùng `(source_id, content_hash, prompt_version)`.

---

## 3. Tiêu chí nghiệm thu (Definition of Done)

- File `db/schema.sql` và `db/repository.py` hoạt động độc lập, không phụ thuộc UI.
- Test `pytest tests/extraction/test_repository.py` đạt 100% passed trên database SQLite in-memory hoặc file tạm (`tmp_path`).
