# Contract: `modules.scheduler`

```python
from modules.scheduler import schedule, ALGORITHMS          # ("EDF", "CP-SAT")
from modules.scheduler.model import ClassSession, ScheduleSettings, ScheduleResult
from modules.scheduler.timetable import load_timetable_csv   # (path|file) -> (sessions, errors)
from modules.scheduler.metrics import evaluate, validate
from modules.scheduler.reminders import make_reminders, to_ics, send_due, TelegramSender

result: ScheduleResult = schedule(tasks, sessions, settings, algorithm="CP-SAT")
#   chỉ dùng task confirmed; task khác bị bỏ qua

validate(result.blocks, tasks, sessions, settings) -> list[str]   # mô tả từng vi phạm; [] = hợp lệ
evaluate(result, tasks, sessions, settings) -> dict               # chỉ số trong research.md R4

make_reminders(blocks, tasks, before_block_min=30, before_deadline_h=24,
               channel=ReminderChannel.TELEGRAM) -> list[Reminder]
to_ics(blocks, tasks, before_block_min=30, before_deadline_h=24) -> str
send_due(reminders, now, send: Callable[[str], None], store_path) -> list[Reminder]  # đã gửi
```
