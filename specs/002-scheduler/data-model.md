# Data Model: Module C (nội bộ `modules/scheduler/model.py`)

Hợp đồng chung dùng lại: `Task` (vào), `StudyBlock`, `Reminder` (ra).

## ClassSession — buổi lên lớp lặp hằng tuần

`weekday: int` (0 = thứ Hai … 6 = Chủ nhật), `start: time`, `end: time` (`end > start`),
`course: str`, `room: str = ""`.

CSV (`data/sample/thoi_khoa_bieu.csv`), cột: `thu,bat_dau,ket_thuc,mon,phong`;
`thu` nhận `2`–`7`, `CN` hoặc `8` (Chủ nhật); giờ dạng `7:00` hoặc `07:00`.

## ScheduleSettings

| Trường | Mặc định | Ràng buộc |
|---|---|---|
| `start` | hôm nay | date |
| `days` | 14 | 1–35 |
| `day_start`, `day_end` | 07:00, 22:00 | `day_end > day_start` |
| `max_hours_per_day` | 4 | > 0 |
| `slot_minutes` | 30 | ước của 60 |
| `not_before` | None | datetime; ô bắt đầu trước mốc này bị bỏ |
| `time_limit_s` | 10 | > 0 |

## Slot (nội bộ)

`index: int`, `start: datetime`, `end: datetime`, `day: date`.

## ScheduleResult

`algorithm: str` (`"EDF"` / `"CP-SAT"`), `blocks: list[StudyBlock]`,
`missing_hours: dict[task_id, float]` (chỉ nhiệm vụ thiếu), `status: str`
(`"OPTIMAL"`, `"FEASIBLE"`, `"GREEDY"`, `"EMPTY"`), `runtime_s: float`.
