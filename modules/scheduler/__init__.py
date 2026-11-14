"""C — Lập lịch & nhắc nhở (Long)
Vào: Task trạng thái confirmed (từ B). Ra: StudyBlock, Reminder.

    from modules.scheduler import schedule
    result = schedule(tasks, sessions, settings, algorithm="CP-SAT")
"""
from __future__ import annotations

import time

from core.contracts import Task, schedulable

from . import cpsat, edf
from .metrics import missing_hours
from .model import ClassSession, ScheduleResult, ScheduleSettings
from .slots import free_slots

SOLVERS = {"EDF": edf.solve, "CP-SAT": cpsat.solve}
ALGORITHMS = tuple(SOLVERS)


def schedule(tasks: list[Task], sessions: list[ClassSession], settings: ScheduleSettings,
             algorithm: str = "CP-SAT") -> ScheduleResult:
    """Xếp lịch cho các nhiệm vụ đã xác nhận; nhiệm vụ khác bị bỏ qua (nguyên tắc I)."""
    if algorithm not in SOLVERS:
        raise ValueError(f"Thuật toán '{algorithm}' không có ({', '.join(ALGORITHMS)})")
    confirmed = schedulable(tasks)
    t0 = time.perf_counter()
    if confirmed:
        blocks, status = SOLVERS[algorithm](confirmed, free_slots(sessions, settings), settings)
    else:
        blocks, status = [], "EMPTY"
    return ScheduleResult(
        algorithm=algorithm, blocks=blocks, status=status,
        missing_hours=missing_hours(blocks, confirmed, settings),
        runtime_s=time.perf_counter() - t0)
