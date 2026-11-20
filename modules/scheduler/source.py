"""Cạnh nối B → C: đọc nhiệm vụ module B đã lưu trong CSDL và đổi sang ``contracts.Task``.

- Bỏ task đã huỷ (``cancelled``).
- Giữ nguyên trạng thái của B: ``confirmed`` được xếp lịch, ``proposed`` chỉ hiện để người dùng
  xác nhận (nguyên tắc I: AI chỉ đề xuất).
- Task thiếu hạn nộp hoặc hạn nộp không đọc được thì không xếp được: trả về trong danh sách bỏ qua
  kèm lý do, không ném lỗi làm hỏng cả trang.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from core.contracts import Task, TaskStatus
from db.repository import Repository
from modules.extraction.workflow import to_contract_task


@dataclass
class Skipped:
    task_id: str
    title: str
    reason: str


def tasks_from_b(repo: Repository) -> tuple[list[Task], list[Skipped]]:
    tasks: list[Task] = []
    skipped: list[Skipped] = []
    for row in repo.list_tasks():
        status = row.get("status")
        if status == TaskStatus.CANCELLED.value:
            continue
        try:
            task = to_contract_task(row, repo, force_schedulable=True)
        except (ValueError, KeyError) as exc:
            skipped.append(Skipped(str(row.get("id")), str(row.get("title") or ""), str(exc)))
            continue
        tasks.append(replace(task, status=TaskStatus(status)))
    tasks.sort(key=lambda t: t.deadline)
    return tasks, skipped
