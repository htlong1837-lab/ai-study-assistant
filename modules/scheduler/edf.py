"""Baseline: Earliest Deadline First (tham lam). Xem research.md R2."""
from __future__ import annotations

from collections import Counter

from core.contracts import Task

from .model import PRIORITY_WEIGHT, ScheduleSettings, Slot
from .slots import to_blocks


def solve(tasks: list[Task], slots: list[Slot], settings: ScheduleSettings):
    """Sắp theo (hạn nộp, ưu tiên giảm); mỗi nhiệm vụ lấy các ô rảnh sớm nhất còn trống."""
    used: set[int] = set()
    day_load: Counter = Counter()
    cap = settings.max_slots_per_day
    assignment = []

    for t in sorted(tasks, key=lambda t: (t.deadline, -PRIORITY_WEIGHT[t.priority], t.id)):
        need = settings.need_slots(t)
        for s in slots:
            if need == 0 or s.end > t.deadline:
                break
            if s.index in used or day_load[s.day] >= cap:
                continue
            used.add(s.index)
            day_load[s.day] += 1
            assignment.append((t.id, s))
            need -= 1
    return to_blocks(assignment), "GREEDY"
