# Contract: `modules.extraction`

Tài liệu giao tiếp nội bộ giữa tầng giao diện, các module khác và logic cốt lõi của Module B.

```python
from datetime import datetime
from typing import Literal

from core.contracts import ClassifiedEmail, ParsedDocument, Task
from core.llm_client import LLMClient
from db.repository import Repository
from modules.extraction.datetime_normalizer import NormalizedDeadline, normalize
from modules.extraction.schemas import RawAssignment, ExtractionResult

# --- 1. Xử lý nguồn dữ liệu đầu vào ---

def process_email(
    email: ClassifiedEmail, 
    llm: LLMClient, 
    repo: Repository
) -> list[str]:
    """Xử lý email an toàn: Trích xuất, chuẩn hóa thời gian, so khớp bài tập cũ.
    Lưu vào DB ở trạng thái 'proposed' (hoặc tạo proposal cập nhật nếu là email dời hạn).
    Trả về danh sách task_id được tạo mới hoặc cập nhật.
    Ném ngoại lệ UnsafeSourceError nếu email không an toàn (can_forward == False)."""


def process_document(
    doc: ParsedDocument, 
    llm: LLMClient, 
    repo: Repository, 
    linked_email: ClassifiedEmail | None = None,
    pages: list[int] | None = None
) -> list[str]:
    """Xử lý tài liệu đề bài: Trích xuất thông tin theo trang, đối chiếu mâu thuẫn 
    với email liên kết (nếu có), lưu vào DB ở trạng thái 'proposed'."""


# --- 2. Vòng đời và Phê duyệt đề xuất (Human-in-the-loop) ---

def confirm(
    task_id: str, 
    repo: Repository, 
    overrides: dict | None = None
) -> Task:
    """Chuyển trạng thái task từ 'proposed' sang 'confirmed'.
    Cho phép sinh viên ghi đè deadline, estimated_hours, priority qua overrides.
    Bắt buộc task phải có deadline hợp lệ mới được xác nhận.
    Ghi nhận confirmed_at và trả về đối tượng Task hợp lệ theo core.contracts.Task."""


def cancel(task_id: str, repo: Repository) -> None:
    """Người dùng từ chối / hủy đề xuất (chuyển sang 'cancelled')."""


# --- 3. Giải quyết mâu thuẫn và Đề xuất dời hạn ---

def resolve_conflict(
    conflict_id: int, 
    choice: Literal['a', 'b', 'manual'], 
    manual_value: str | None = None, 
    repo: Repository = ...
) -> None:
    """Người dùng lựa chọn phương án giải quyết mâu thuẫn giữa 2 nguồn."""


def accept_update_proposal(proposal_id: int, repo: Repository) -> Task:
    """Người dùng chấp nhận đề xuất dời hạn / thay đổi yêu cầu cho bài tập đã tồn tại.
    Cập nhật giá trị mới vào bảng tasks và trả về Task đã cập nhật."""


def reject_update_proposal(proposal_id: int, repo: Repository) -> None:
    """Người dùng từ chối đề xuất dời hạn (giữ nguyên thông tin cũ của task)."""


# --- 4. Cầu nối chuyển giao sang Module C ---

def to_contract_task(task_row: dict) -> Task:
    """Chuyển đổi bản ghi DB sang dataclass core.contracts.Task.
    Chỉ cho phép chuyển đổi nếu status == 'confirmed' và deadline is not None."""
```
