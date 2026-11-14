"""Kiểu dữ liệu nội bộ của module C. Hợp đồng ra/vào dùng core.contracts."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, time

from core.contracts import Priority, StudyBlock, Task

PRIORITY_WEIGHT = {Priority.LOW: 1, Priority.MEDIUM: 2, Priority.HIGH: 3}
WEEKDAY_VN = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]


@dataclass
class ClassSession:
    """Buổi lên lớp lặp lại hằng tuần."""
    weekday: int  # 0 = thứ Hai ... 6 = Chủ nhật
    start: time
    end: time
    course: str
    room: str = ""

    def __post_init__(self):
        if not 0 <= self.weekday <= 6:
            raise ValueError(f"weekday phải 0–6, nhận {self.weekday}")
        if self.end <= self.start:
            raise ValueError("giờ kết thúc phải sau giờ bắt đầu")

    def on(self, day: date) -> tuple[datetime, datetime] | None:
        """Khoảng thời gian của buổi học trong ngày `day`, None nếu không học ngày đó."""
        if day.weekday() != self.weekday:
            return None
        return datetime.combine(day, self.start), datetime.combine(day, self.end)


@dataclass
class ScheduleSettings:
    start: date = field(default_factory=date.today)
    days: int = 14
    day_start: time = time(7, 0)
    day_end: time = time(22, 0)
    max_hours_per_day: float = 4.0
    slot_minutes: int = 30
    min_block_minutes: int = 60
    not_before: datetime | None = None
    time_limit_s: float = 10.0

    def __post_init__(self):
        if not 1 <= self.days <= 35:
            raise ValueError("days phải trong khoảng 1–35")
        if self.day_end <= self.day_start:
            raise ValueError("day_end phải sau day_start")
        if self.max_hours_per_day <= 0:
            raise ValueError("max_hours_per_day phải > 0")
        if self.slot_minutes <= 0 or 60 % self.slot_minutes:
            raise ValueError("slot_minutes phải là ước của 60")
        if self.min_block_minutes < self.slot_minutes or self.min_block_minutes % self.slot_minutes:
            raise ValueError("min_block_minutes phải là bội của slot_minutes")
        if self.time_limit_s <= 0:
            raise ValueError("time_limit_s phải > 0")

    @property
    def slot_hours(self) -> float:
        return self.slot_minutes / 60

    @property
    def max_slots_per_day(self) -> int:
        return int(self.max_hours_per_day * 60 // self.slot_minutes)

    @property
    def min_block_slots(self) -> int:
        return self.min_block_minutes // self.slot_minutes

    def need_slots(self, task: Task) -> int:
        """Số ô cần cho nhiệm vụ, làm tròn lên."""
        return math.ceil(round(task.estimated_hours * 60 / self.slot_minutes, 6))


@dataclass(frozen=True)
class Slot:
    index: int
    start: datetime
    end: datetime

    @property
    def day(self) -> date:
        return self.start.date()


@dataclass
class ScheduleResult:
    algorithm: str
    blocks: list[StudyBlock]
    missing_hours: dict[str, float]
    status: str
    runtime_s: float = 0.0
