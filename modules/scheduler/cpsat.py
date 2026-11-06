"""Xếp lịch bằng thỏa mãn ràng buộc có tối ưu (OR-Tools CP-SAT). Xem research.md R3.

Biến   x[t,s]   ô s dành cho nhiệm vụ t (chỉ tạo khi ô kết thúc trước hạn của t)
       short_t  số ô còn thiếu của t
       load_d   số ô dùng trong ngày d;  peak = max load_d
       y[t,s]   ô s mở đầu một khối mới của t
Ràng buộc  mỗi ô ≤ 1 nhiệm vụ;  Σ_s x[t,s] + short_t = need_t;  load_d ≤ M;
           y[t,s] ≥ x[t,s] − x[t,s−1] (ô liền trước cùng ngày);
           y[t,s] ⇒ x[t,s+j] với j < min(k, need_t)  (khối dài tối thiểu k ô)
Mục tiêu   min 10000·Σ w_t·short_t + 100·peak + Σ y
"""
from __future__ import annotations

from collections import defaultdict

from ortools.sat.python import cp_model

from core.contracts import Task

from .model import PRIORITY_WEIGHT, ScheduleSettings, Slot
from .slots import to_blocks

W_SHORT, W_PEAK, W_BLOCK = 10_000, 100, 1


def solve(tasks: list[Task], slots: list[Slot], settings: ScheduleSettings):
    model = cp_model.CpModel()
    cap = settings.max_slots_per_day

    x: dict[tuple[str, int], cp_model.IntVar] = {}
    by_slot, by_task, by_day = defaultdict(list), defaultdict(list), defaultdict(list)
    for t in tasks:
        for s in slots:
            if s.end <= t.deadline:
                v = model.new_bool_var(f"x_{t.id}_{s.index}")
                x[t.id, s.index] = v
                by_slot[s.index].append(v)
                by_task[t.id].append(v)
                by_day[s.day].append(v)

    # 1. Mỗi ô tối đa một nhiệm vụ.
    for vs in by_slot.values():
        model.add_at_most_one(vs)

    # 2. Đủ giờ, hoặc ghi nhận phần thiếu (ràng buộc mềm).
    short = {}
    for t in tasks:
        need = settings.need_slots(t)
        short[t.id] = model.new_int_var(0, need, f"short_{t.id}")
        model.add(sum(by_task[t.id]) + short[t.id] == need)

    # 3. Giờ tối đa mỗi ngày và tải đỉnh.
    loads = []
    for day, vs in by_day.items():
        load = model.new_int_var(0, cap, f"load_{day}")
        model.add(load == sum(vs))
        loads.append(load)
    peak = model.new_int_var(0, cap, "peak")
    if loads:
        model.add_max_equality(peak, loads)

    # 4. Đếm số khối (ô bắt đầu một đoạn liên tục) và độ dài khối tối thiểu:
    #    nếu y[t,s] = 1 thì k_t − 1 ô liền sau cũng thuộc t (k_t = min(k, need_t)).
    def contiguous(i: int) -> bool:
        return 0 < i < len(slots) and slots[i - 1].end == slots[i].start

    need = {t.id: settings.need_slots(t) for t in tasks}
    starts = []
    for (tid, i), v in x.items():
        y = model.new_bool_var(f"y_{tid}_{i}")
        prev = x.get((tid, i - 1)) if contiguous(i) else None
        model.add(y >= v - prev) if prev is not None else model.add(y >= v)
        for j in range(1, min(settings.min_block_slots, need[tid])):
            nxt = x.get((tid, i + j)) if contiguous(i + j) else None
            if nxt is None:
                model.add(y == 0)  # không đủ chỗ liền sau để làm một khối đủ dài
                break
            model.add_implication(y, nxt)
        starts.append(y)

    model.minimize(
        W_SHORT * sum(PRIORITY_WEIGHT[t.priority] * short[t.id] for t in tasks)
        + W_PEAK * peak + W_BLOCK * sum(starts))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = settings.time_limit_s
    solver.parameters.num_workers = 8
    solver.parameters.random_seed = 0
    # Dừng khi khoảng cách tới cận dưới < W_PEAK: lúc đó thiếu giờ và tải đỉnh đã được chứng
    # minh tối ưu, chỉ còn số khối có thể chưa tối ưu. Tránh mất trọn time limit vì đối xứng.
    solver.parameters.absolute_gap_limit = W_PEAK - 1
    status = solver.solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return [], solver.status_name(status)
    by_index = {s.index: s for s in slots}
    assignment = [(tid, by_index[i]) for (tid, i), v in x.items() if solver.value(v)]
    return to_blocks(assignment), solver.status_name(status)
