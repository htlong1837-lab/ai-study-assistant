"""Kiểm tra ràng buộc và tính chỉ số — dùng chung cho mọi thuật toán (research R4)."""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import timedelta

from core.contracts import StudyBlock, Task, schedulable

from .model import PRIORITY_WEIGHT, ClassSession, ScheduleResult, ScheduleSettings
from .slots import busy_intervals

EPS = 1e-9


def validate(blocks: list[StudyBlock], tasks: list[Task], sessions: list[ClassSession],
             settings: ScheduleSettings) -> list[str]:
    """Danh sách vi phạm ràng buộc cứng; rỗng nghĩa là lịch hợp lệ."""
    errors = []
    by_id = {t.id: t for t in schedulable(tasks)}
    busy = busy_intervals(sessions, settings)

    for b in blocks:
        label = f"{b.task_id} {b.start:%d/%m %H:%M}-{b.end:%H:%M}"
        task = by_id.get(b.task_id)
        if task is None:
            errors.append(f"{label}: nhiệm vụ không tồn tại hoặc chưa được xác nhận")
        elif b.end > task.deadline:
            errors.append(f"{label}: kết thúc sau hạn nộp")
        if b.start.date() != b.end.date() or b.start.time() < settings.day_start \
                or b.end.time() > settings.day_end:
            errors.append(f"{label}: ngoài khung giờ học")
        for b0, b1, s in busy:
            if b0 < b.end and b.start < b1:
                errors.append(f"{label}: trùng giờ lên lớp {s.course}")

    ordered = sorted(blocks, key=lambda b: b.start)
    for a, b in zip(ordered, ordered[1:]):
        if b.start < a.end:
            errors.append(f"{a.task_id} và {b.task_id} trùng giờ lúc {b.start:%d/%m %H:%M}")

    for day, hours in daily_hours(blocks).items():
        if hours > settings.max_hours_per_day + EPS:
            errors.append(f"{day:%d/%m}: {hours:g} giờ, vượt tối đa {settings.max_hours_per_day:g}")
    return errors


def daily_hours(blocks: list[StudyBlock]) -> dict:
    load = defaultdict(float)
    for b in blocks:
        load[b.start.date()] += b.hours
    return dict(load)


def short_blocks(blocks: list[StudyBlock], tasks: list[Task], settings: ScheduleSettings) -> int:
    """Số khối ngắn hơn độ dài tối thiểu (trừ nhiệm vụ vốn cần ít giờ hơn mức đó)."""
    need = {t.id: settings.need_slots(t) * settings.slot_hours for t in tasks}
    floor = settings.min_block_minutes / 60
    return sum(b.hours < min(floor, need.get(b.task_id, floor)) - EPS for b in blocks)


def missing_hours(blocks: list[StudyBlock], tasks: list[Task],
                  settings: ScheduleSettings) -> dict[str, float]:
    """Số giờ còn thiếu của từng nhiệm vụ đã xác nhận (chỉ trả nhiệm vụ thiếu)."""
    got = defaultdict(float)
    for b in blocks:
        got[b.task_id] += b.hours
    out = {}
    for t in schedulable(tasks):
        need = settings.need_slots(t) * settings.slot_hours
        short = need - got[t.id]
        if short > EPS:
            out[t.id] = round(short, 4)
    return out


def evaluate(result: ScheduleResult, tasks: list[Task], sessions: list[ClassSession],
             settings: ScheduleSettings) -> dict:
    confirmed = schedulable(tasks)
    missing = missing_hours(result.blocks, tasks, settings)
    weights = {t.id: PRIORITY_WEIGHT[t.priority] for t in confirmed}

    # Độ lệch tải tính trên các ngày từ đầu đến hạn cuối (trong phạm vi xếp lịch).
    last = max((t.deadline.date() for t in confirmed), default=settings.start)
    end = min(last, settings.start + timedelta(days=settings.days - 1))
    span = [settings.start + timedelta(days=i) for i in range((end - settings.start).days + 1)]
    load = daily_hours(result.blocks)
    per_day = [load.get(d, 0.0) for d in span] or [0.0]

    return {
        "Thuật toán": result.algorithm,
        "Kịp hạn": f"{len(confirmed) - len(missing)}/{len(confirmed)}",
        "Giờ thiếu": round(sum(missing.values()), 2),
        "Giờ thiếu (trọng số)": round(sum(weights[k] * v for k, v in missing.items()), 2),
        "Xung đột": len(validate(result.blocks, tasks, sessions, settings)),
        "Đỉnh tải (giờ/ngày)": round(max(per_day), 2),
        "Độ lệch tải": round(statistics.pstdev(per_day), 2),
        "Số khối học": len(result.blocks),
        f"Khối < {settings.min_block_minutes} phút": short_blocks(result.blocks, tasks, settings),
        "Thời gian chạy (s)": round(result.runtime_s, 3),
        "Trạng thái": result.status,
    }
