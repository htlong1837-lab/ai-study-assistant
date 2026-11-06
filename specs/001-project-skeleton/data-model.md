# Data Model: Hợp đồng dữ liệu chung (`core/contracts.py`)

Luồng: `D → (ClassifiedEmail, SafeAttachment) → A/B`, `A → ParsedDocument → B`,
`B → Task → C`, `C → StudyBlock, Reminder → người dùng`.

## Enum

| Enum | Giá trị |
|---|---|
| `SafetyStatus` | `safe`, `suspicious`, `malicious` |
| `EmailLabel` | `assignment`, `schedule`, `announcement`, `spam`, `phishing`, `other` |
| `TaskStatus` | `proposed`, `confirmed`, `cancelled` |
| `Priority` | `low`, `medium`, `high` |
| `ReminderChannel` | `telegram`, `email`, `ics`, `in_app` |

## ClassifiedEmail (D → B)

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| `id` | str | không rỗng |
| `sender`, `subject`, `body` | str | |
| `received_at` | datetime | |
| `label` | EmailLabel | |
| `safety` | SafetyStatus | |
| `summary` | str \| None | |
| `attachments` | list[str] | đường dẫn file gốc |
| `label_confidence` | float | 0 ≤ x ≤ 1 |

## SafeAttachment (D → A)

`path: str`, `sha256: str` (64 ký tự hex), `email_id: str`. Chỉ được tạo cho email đã qua `can_forward`.

## ParsedDocument (A → B)

`doc_id: str`, `filename: str`, `pages: list[Page]`; `Page(number: int ≥ 1, text: str)`.
Số trang không trùng nhau. Có `text_of(numbers)` để lấy văn bản theo trang.

## Task (B → C)

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| `id` | str | không rỗng |
| `title`, `course` | str | `title` không rỗng |
| `deadline` | datetime | bắt buộc |
| `estimated_hours` | float | > 0 |
| `priority` | Priority | mặc định `medium` |
| `source` | str | ví dụ `"email:e-001"`, `"de_bai.pdf#p2"` |
| `confidence` | float | 0 ≤ x ≤ 1 |
| `status` | TaskStatus | mặc định `proposed` |

Chuyển trạng thái: `proposed → confirmed`, `proposed → cancelled`, `confirmed → cancelled`.

## StudyBlock (C → người dùng)

`task_id: str`, `start: datetime`, `end: datetime` (`end > start`); thuộc tính `hours`.

## Reminder (C → người dùng)

`task_id: str`, `remind_at: datetime`, `channel: ReminderChannel`, `message: str`.

## Hàm quy tắc

- `can_forward(email, allow_suspicious=False) -> bool` — nguyên tắc II.
- `schedulable(tasks) -> list[Task]` — chỉ trả task `confirmed` (nguyên tắc I).
