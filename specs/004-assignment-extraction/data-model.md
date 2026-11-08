# Data Model: Module B — Trích xuất yêu cầu bài tập

Tài liệu đặc tả mô hình dữ liệu nội bộ và ánh xạ sang hợp đồng chung (`core/contracts.py`).

## 1. Hợp đồng dữ liệu trao đổi giữa các Module (`core/contracts.py`)

- **Đầu vào từ Module D**: `ClassifiedEmail(id, sender, subject, body, received_at, label, safety, summary, attachments, label_confidence)`.
  - Chỉ xử lý khi `can_forward(email) == True` (`safety == SafetyStatus.SAFE`).
- **Đầu vào từ Module A**: `ParsedDocument(doc_id, filename, pages: list[Page(number, text)])`.
- **Đầu ra gửi sang Module C**: `Task(id, title, course, deadline, estimated_hours, priority, source, confidence, status)`.
  - Chỉ chuyển sang Module C khi `status == TaskStatus.CONFIRMED` (thông qua hàm `schedulable()`).

---

## 2. Mô hình Pydantic Trích xuất Nội bộ (`modules/extraction/schemas.py`)

Mọi trường dữ liệu trích xuất từ LLM đều có cấu trúc kèm bằng chứng:

```python
class Evidence(BaseModel):
    quote: str = Field(description="Trích nguyên văn cụm từ trong văn bản, không diễn đạt lại")
    location: str = Field(description="'email' hoặc 'p<số trang>'")

class ExField(BaseModel, Generic[T]):
    value: T | None = None
    evidence: Evidence | None = None

class RawDeadline(BaseModel):
    label: str | None = None          # "nộp báo cáo", "demo"...
    raw_text: str                     # Cụm thời gian nguyên văn
    evidence: Evidence

class RawAssignment(BaseModel):
    title: ExField[str]
    course: ExField[str]
    deadlines: list[RawDeadline] = []
    submission_platform: ExField[str]
    submission_format: ExField[list[str]]
    naming_convention: ExField[str]
    grading_criteria: ExField[list[str]]
    estimated_hours: float | None = None
    priority_suggestion: Priority | None = None
    is_extension_notice: bool = False
    refers_to: str | None = None

class ExtractionResult(BaseModel):
    assignments: list[RawAssignment] = []
    not_assignment: bool = False
```

---

## 3. Cấu trúc Chuẩn hóa Ngày giờ (`modules/extraction/datetime_normalizer.py`)

```python
@dataclass
class NormalizedDeadline:
    value: datetime | None           # tz-aware Asia/Ho_Chi_Minh; None nếu không thể phân giải
    anchor: datetime                 # Mốc neo (received_at hoặc ngày tài liệu)
    rule_id: str | None
    assumptions: list[str]           # Các giả định bằng tiếng Việt để hiển thị trên UI
    flags: list[str]                 # 'OUTDATED_DEADLINE', 'AMBIGUOUS', 'UNRESOLVED'
    time_defaulted: bool             # True nếu giờ do hệ thống tự gán 23:59:00
```

---

## 4. Cơ sở dữ liệu Nội bộ SQLite (`db/schema.sql`)

### Bảng `tasks`
Lưu trữ nhiệm vụ ở các trạng thái vòng đời. Điểm khác biệt quan trọng với `core/contracts.Task`: Trường `deadline` ở bảng này cho phép `NULL` khi ở trạng thái `proposed` (để lưu trữ đề xuất chưa tìm thấy hạn nộp).
- `id` (TEXT, PK): Mã nhiệm vụ (ví dụ: `task-2026-001`).
- `title` (TEXT, NOT NULL): Tên bài tập.
- `course` (TEXT): Tên môn học.
- `deadline` (TEXT): Chuỗi ISO-8601 kèm múi giờ (NULL khi chưa phân giải được).
- `estimated_hours` (REAL): Số giờ ước tính (NULL khi chưa ước lượng).
- `priority` (TEXT, NOT NULL DEFAULT 'medium'): 'low', 'medium', 'high'.
- `confidence` (REAL, NOT NULL): Điểm tin cậy (0.0 – 1.0).
- `status` (TEXT, NOT NULL): 'proposed', 'confirmed', 'cancelled'.
- `created_at` (TEXT, NOT NULL): ISO timestamp tạo đề xuất.
- `confirmed_at` (TEXT): ISO timestamp sinh viên phê duyệt.

### Bảng `task_sources`
Lưu nguồn gốc của từng trường dữ liệu phục vụ đối chiếu:
- `id` (INTEGER, PK AUTOINCREMENT)
- `task_id` (TEXT, FK tasks.id ON DELETE CASCADE)
- `source` (TEXT, NOT NULL): 'email:<id>' hoặc 'doc:<doc_id>#p<n>'
- `field` (TEXT): Tên trường được trích xuất từ nguồn này
- `quote` (TEXT): Đoạn trích dẫn nguyên văn
- `kind` (TEXT, NOT NULL): 'email' hoặc 'document'

### Bảng `assignment_details`
Thông tin mở rộng về quy cách nộp bài và tiêu chí chấm điểm:
- `task_id` (TEXT, PK, FK tasks.id ON DELETE CASCADE)
- `raw_deadline_text` (TEXT): Cụm từ hạn nộp nguyên văn
- `submission_format` (TEXT): JSON array các định dạng file cho phép (ví dụ `[".pdf", ".zip"]`)
- `submission_platform` (TEXT): Nền tảng nộp bài (LMS, Drive, Email, GitHub...)
- `naming_convention` (TEXT): Quy cách đặt tên file
- `grading_criteria` (TEXT): JSON array các tiêu chí đánh giá
- `assumptions` (TEXT): JSON array các giả định khi chuẩn hóa thời gian

### Bảng `conflicts`
Lưu trữ các bất đồng và mâu thuẫn giữa 2 nguồn:
- `id` (INTEGER, PK AUTOINCREMENT)
- `task_id` (TEXT, FK tasks.id ON DELETE CASCADE)
- `kind` (TEXT, NOT NULL): 'deadline', 'submission', 'ambiguity', 'outdated'
- `value_a` (TEXT), `source_a` (TEXT)
- `value_b` (TEXT), `source_b` (TEXT)
- `suggestion` (TEXT): 'a', 'b', hoặc NULL
- `resolution` (TEXT): 'a', 'b', 'manual', hoặc NULL
- `resolved_at` (TEXT)

### Bảng `task_update_proposals`
Đề xuất thay đổi cho nhiệm vụ đã tồn tại khi nhận được thông báo dời hạn mới:
- `id` (INTEGER, PK AUTOINCREMENT)
- `task_id` (TEXT, FK tasks.id ON DELETE CASCADE)
- `field` (TEXT, NOT NULL): Tên trường thay đổi (ví dụ: 'deadline')
- `old_value` (TEXT), `new_value` (TEXT)
- `source` (TEXT, NOT NULL), `quote` (TEXT)
- `status` (TEXT, NOT NULL DEFAULT 'pending'): 'pending', 'accepted', 'rejected'
- `created_at` (TEXT, NOT NULL)

### Bảng `extraction_logs`
Lưu nhật ký token và kiểm tra bộ nhớ đệm:
- `id` (INTEGER, PK AUTOINCREMENT)
- `source_type` (TEXT, NOT NULL): 'email' hoặc 'document'
- `source_id` (TEXT, NOT NULL)
- `content_hash` (TEXT, NOT NULL): SHA-256 nội dung văn bản nguồn
- `prompt_version` (TEXT, NOT NULL): Phiên bản prompt ('v1', 'v2'...)
- `model_name` (TEXT, NOT NULL)
- `prompt_tokens` (INTEGER), `completion_tokens` (INTEGER)
- `execution_time_ms` (REAL)
- `raw_response` (TEXT)
- `created_at` (TEXT, NOT NULL)
- Ràng buộc duy nhất: `UNIQUE(source_id, content_hash, prompt_version)`
