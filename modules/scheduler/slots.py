"""Rời rạc hoá thời gian thành ô rảnh và gộp ô thành khối học."""
from __future__ import annotations

from datetime import datetime, timedelta

from core.contracts import StudyBlock

from .model import ClassSession, ScheduleSettings, Slot


def busy_intervals(sessions: list[ClassSession], settings: ScheduleSettings):
    """Mọi khoảng lên lớp trong phạm vi xếp lịch."""
    out = []
    for i in range(settings.days):
        day = settings.start + timedelta(days=i)
        for s in sessions:
            interval = s.on(day)
            if interval:
                out.append((*interval, s))
    return out


def free_slots(sessions: list[ClassSession], settings: ScheduleSettings) -> list[Slot]:
    """Các ô nằm trọn trong khung giờ học, không giao giờ lên lớp, sau `not_before`."""
    busy = busy_intervals(sessions, settings)
    step = timedelta(minutes=settings.slot_minutes)
    slots: list[Slot] = []
    for i in range(settings.days):
        day = settings.start + timedelta(days=i)
        t = datetime.combine(day, settings.day_start)
        day_end = datetime.combine(day, settings.day_end)
        while t + step <= day_end:
            end = t + step
            overlaps = any(b0 < end and t < b1 for b0, b1, _ in busy)
            late = settings.not_before is not None and t < settings.not_before
            if not overlaps and not late:
                slots.append(Slot(len(slots), t, end))
            t = end
    return slots


def to_blocks(assignment: list[tuple[str, Slot]]) -> list[StudyBlock]:
    """Gộp các ô liền nhau của cùng nhiệm vụ thành một StudyBlock."""
    blocks: list[StudyBlock] = []
    for task_id, slot in sorted(assignment, key=lambda a: a[1].start):
        last = blocks[-1] if blocks else None
        if last and last.task_id == task_id and last.end == slot.start:
            last.end = slot.end
        else:
            blocks.append(StudyBlock(task_id=task_id, start=slot.start, end=slot.end))
    return blocks
