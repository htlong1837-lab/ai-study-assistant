"""Bộ sinh kịch bản thí nghiệm có hạt giống (specs/003-scheduler-experiments/plan.md)."""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from core.config import SAMPLE_DIR
from core.contracts import Priority, Task, TaskStatus
from modules.scheduler.model import ClassSession, ScheduleSettings
from modules.scheduler.slots import free_slots
from modules.scheduler.timetable import load_timetable_csv

START = date(2026, 11, 9)  # thứ Hai


@dataclass(frozen=True)
class Scenario:
    name: str
    n_tasks: int
    hours: tuple[int, ...]
    deadline_days: tuple[int, int]  # ngày thứ (tính từ START), gồm cả hai đầu


SCENARIOS = {
    "Nhẹ": Scenario("Nhẹ", 6, (2, 3, 4), (7, 27)),
    "Vừa": Scenario("Vừa", 12, (2, 3, 4, 6), (5, 27)),
    "Quá tải": Scenario("Quá tải", 18, (3, 4, 6, 8), (3, 20)),
}


def base_settings(time_limit_s: float = 10) -> ScheduleSettings:
    return ScheduleSettings(start=START, days=28, day_start=time(7), day_end=time(22),
                            max_hours_per_day=4, min_block_minutes=60, time_limit_s=time_limit_s)


def sessions() -> list[ClassSession]:
    return load_timetable_csv(SAMPLE_DIR / "thoi_khoa_bieu.csv")[0]


def generate(name: str, seed: int) -> list[Task]:
    """Danh sách nhiệm vụ đã xác nhận cho kịch bản `name`; cùng seed → cùng dữ liệu."""
    sc = SCENARIOS[name]
    rng = random.Random(f"{name}-{seed}")
    lo, hi = sc.deadline_days
    return [Task(
        id=f"{name[:2]}{seed}-{i:02d}", title=f"Việc {i + 1}", course="Thí nghiệm",
        deadline=datetime.combine(START + timedelta(days=rng.randint(lo, hi)), time(23, 59)),
        estimated_hours=rng.choice(sc.hours), source="synthetic", confidence=1.0,
        priority=rng.choice(list(Priority)), status=TaskStatus.CONFIRMED,
    ) for i in range(sc.n_tasks)]


def load_ratio(tasks: list[Task], sess: list[ClassSession], settings: ScheduleSettings) -> float:
    """Giờ cần làm / giờ có thể học (đã tính giới hạn mỗi ngày) đến hạn cuối."""
    last = max(t.deadline for t in tasks)
    per_day = Counter(s.day for s in free_slots(sess, settings) if s.end <= last)
    capacity = sum(min(n, settings.max_slots_per_day) for n in per_day.values()) * settings.slot_hours
    need = sum(settings.need_slots(t) for t in tasks) * settings.slot_hours
    return need / capacity
