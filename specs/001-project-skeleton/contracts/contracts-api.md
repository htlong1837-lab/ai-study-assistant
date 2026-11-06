# Contract: `core.contracts` và `core.mocks`

Định nghĩa trường xem [data-model.md](../data-model.md).

```python
from core.contracts import (ClassifiedEmail, SafeAttachment, ParsedDocument, Page,
                            Task, StudyBlock, Reminder, can_forward, schedulable)
from core import mocks

mocks.emails()          -> list[ClassifiedEmail]   # ≥ 3, có đủ safe / suspicious / malicious
mocks.attachments()     -> list[SafeAttachment]    # ≥ 3, chỉ từ email safe
mocks.documents()       -> list[ParsedDocument]    # ≥ 3
mocks.tasks()           -> list[Task]              # ≥ 3, có proposed và confirmed
mocks.study_blocks()    -> list[StudyBlock]        # ≥ 3, từ task confirmed
mocks.reminders()       -> list[Reminder]          # ≥ 3
```

- Dữ liệu tạo sai ràng buộc → `ValueError` với thông báo nêu tên trường.
- Hàm mock trả bản mới mỗi lần gọi (sửa không ảnh hưởng lần sau).
- Mốc thời gian trong mock tính tương đối từ `mocks.BASE_TIME` (cố định) để test ổn định.
