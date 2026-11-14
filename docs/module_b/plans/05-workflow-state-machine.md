# Sub-Plan 5: Quy trình Nghiệp vụ & Máy Trạng thái (FR-B04)

> **Mục tiêu:** Xây dựng máy trạng thái quản lý toàn bộ vòng đời nhiệm vụ, đảm bảo thực thi triệt để Nguyên tắc I ("AI chỉ đề xuất, người dùng quyết định"), các hàm xử lý đầu vào từ email/document, và hàm chuyển đổi sang contract `core/contracts.Task`.  
> **Ước tính thời gian:** 3 giờ  
> **Phase tương ứng:** Phase 6

---

## 1. Thiết kế Máy Trạng thái & API (`modules/extraction/workflow.py`)

### 1.1. Luồng chuyển đổi trạng thái (State Lifecycle)
```
               [AI Extractor]
                     │
                     ▼
             ┌───────────────┐
             │   PROPOSED    │ ◄─── (Tạo mới, deadline có thể NULL)
             └───────┬───────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
   [Hủy đề xuất]           [Người dùng xác nhận]
┌─────────────────┐     ┌─────────────────┐
│    CANCELLED    │     │    CONFIRMED    │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                     (Lộ diện cho Module C xếp lịch)
```

Quy tắc bất biến:
1. Nhiệm vụ mới tạo ra luôn có trạng thái `TaskStatus.PROPOSED`.
2. Hàm `confirm()` là con đường **DUY NHẤT** để chuyển một task sang `TaskStatus.CONFIRMED`.
3. Không thể chuyển trạng thái `CANCELLED` trực tiếp thành `CONFIRMED` (phải tạo lại đề xuất mới).
4. `confirm()` sẽ **thất bại** nếu task chưa có hạn nộp (`deadline is None`) hoặc vẫn còn mâu thuẫn (`conflict`) chưa được người dùng giải quyết (chọn phương án A, B hoặc nhập thủ công).

### 1.2. Danh mục các hàm nghiệp vụ chính
```python
def process_email(email: ClassifiedEmail, llm: LLMClient, repo: Repository) -> list[str]:
    """Xử lý email an toàn: Trích xuất, chuẩn hóa, so khớp task cũ, lưu vào DB và trả về danh sách task_id tạo mới/cập nhật."""

def process_document(doc: ParsedDocument, llm: LLMClient, repo: Repository, linked_email: ClassifiedEmail | None = None) -> list[str]:
    """Xử lý tài liệu bài tập từ Module A: Trích xuất, so sánh mâu thuẫn với email liên kết (nếu có) và lưu task proposed."""

def confirm(task_id: str, repo: Repository, overrides: dict | None = None) -> Task:
    """Người dùng xác nhận đề xuất. Cho phép ghi đè các trường (deadline, estimated_hours, priority).
    Chuyển trạng thái sang CONFIRMED, ghi nhận confirmed_at và trả về Task theo hợp đồng core/contracts.py."""

def cancel(task_id: str, repo: Repository) -> None:
    """Người dùng từ chối / hủy đề xuất bài tập."""

def resolve_conflict(conflict_id: int, choice: Literal['a', 'b', 'manual'], manual_value: str | None = None, repo: Repository = ...) -> None:
    """Người dùng giải quyết xung đột trên giao diện."""

def accept_update_proposal(proposal_id: int, repo: Repository) -> Task:
    """Người dùng chấp nhận đề xuất dời hạn / thay đổi yêu cầu cho task đã có."""

def reject_update_proposal(proposal_id: int, repo: Repository) -> None:
    """Người dùng từ chối đề xuất dời hạn."""

def to_contract_task(task_row: dict) -> Task:
    """Chuyển đổi bản ghi DB sang dataclass Task của core/contracts.py.
    Chỉ cho phép chuyển đổi nếu status == CONFIRMED và deadline is not None."""
```

---

## 2. Nhiệm vụ chi tiết (Checklist)

- [ ] **T05.1 — Cài đặt `modules/extraction/workflow.py`:**
  - Cài đặt `process_email` và `process_document` kết nối từ `gate`, `extractor`, `matcher`, `conflicts` vào `repository`.
  - Cài đặt máy trạng thái: `confirm()`, `cancel()`, `resolve_conflict()`.
  - Cài đặt quản lý đề xuất dời hạn: `accept_update_proposal()`, `reject_update_proposal()`.
  - Cài đặt hàm cầu nối `to_contract_task(row)`.
- [ ] **T05.2 — Kiểm thử đơn vị `tests/extraction/test_workflow.py`:**
  - Test vòng đời trạng thái: Tạo `proposed` $\rightarrow$ `confirm()` thành `confirmed`.
  - Test từ chối xác nhận khi task chưa có deadline (phải truyền override deadline mới thành công).
  - Test từ chối xác nhận khi còn conflict chưa resolve.
  - Test không cho phép chuyển từ `cancelled` sang `confirmed`.
  - Test kịch bản đề xuất dời hạn: Nhận proposal $\rightarrow$ `accept_update_proposal` cập nhật hạn mới vào task.
  - Test bảo vệ: Chứng minh trong toàn bộ module không có bất kỳ dòng code nào tạo task `confirmed` mà không qua hàm `confirm()`.

---

## 3. Tiêu chí nghiệm thu (Definition of Done)

- 100% test trong `test_workflow.py` xanh.
- Đảm bảo tính toàn vẹn với `core/contracts.py`: Không ném ngoại lệ khi chuyển đổi task đã xác nhận sang `contracts.Task`.
