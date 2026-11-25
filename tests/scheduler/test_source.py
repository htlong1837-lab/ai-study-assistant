"""Cạnh nối B → C: nhiệm vụ B lưu trong CSDL được đổi sang contracts.Task cho C."""
from datetime import date, datetime
from pathlib import Path

from core.contracts import TaskStatus
from db.repository import Repository
from modules.scheduler import schedule
from modules.scheduler.model import ScheduleSettings
from modules.scheduler.source import tasks_from_b


def _add(repo, tid, status, deadline="2026-11-27T23:59:00", **kw):
    repo.create_task({
        "id": tid, "title": kw.get("title", f"Bài {tid}"), "course": "AI",
        "deadline": deadline, "estimated_hours": kw.get("hours", 3.0),
        "priority": "high", "confidence": 0.9, "status": status,
        "created_at": "2026-11-20T08:00:00",
    })


def test_reads_b_tasks_keeping_status(tmp_path):
    repo = Repository(tmp_path / "b.db")
    _add(repo, "t-1", "confirmed", deadline="2026-11-28T23:59:00")
    _add(repo, "t-2", "proposed", deadline="2026-11-25T23:59:00")
    _add(repo, "t-3", "cancelled")
    repo.add_sources("t-1", [{"source": "email:e-9", "field": "title", "quote": "Bài t-1", "kind": "email"}])

    tasks, skipped = tasks_from_b(repo)

    assert [t.id for t in tasks] == ["t-2", "t-1"]  # sắp theo hạn nộp, bỏ task đã huỷ
    assert {t.id: t.status for t in tasks} == {"t-1": TaskStatus.CONFIRMED, "t-2": TaskStatus.PROPOSED}
    assert tasks[1].source == "email:e-9"
    assert tasks[1].deadline == datetime(2026, 11, 28, 23, 59)
    assert skipped == []


def test_task_without_deadline_is_skipped_with_reason(tmp_path):
    repo = Repository(tmp_path / "b.db")
    _add(repo, "t-1", "confirmed", deadline=None, title="Thiếu hạn")
    tasks, skipped = tasks_from_b(repo)
    assert tasks == []
    assert [(s.task_id, s.title) for s in skipped] == [("t-1", "Thiếu hạn")]
    assert "deadline" in skipped[0].reason


def test_empty_db_gives_nothing(tmp_path):
    assert tasks_from_b(Repository(tmp_path / "b.db")) == ([], [])


def test_only_confirmed_b_tasks_get_scheduled(tmp_path):
    repo = Repository(tmp_path / "b.db")
    _add(repo, "t-1", "confirmed", hours=2.0)
    _add(repo, "t-2", "proposed", hours=2.0)
    tasks, _ = tasks_from_b(repo)
    settings = ScheduleSettings(start=date(2026, 11, 21), days=5)
    for algo in ("EDF", "CP-SAT"):
        r = schedule(tasks, [], settings, algo)
        assert {b.task_id for b in r.blocks} == {"t-1"}


def test_scheduler_page_uses_b_tasks(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    import views._account as account
    from core.workspace import Workspace
    ws = Workspace(tmp_path, "sv@gmail.com")  # người đã đăng nhập: dữ liệu nằm trong thư mục riêng
    repo = Repository(ws.db_path)
    _add(repo, "t-b1", "confirmed", title="Báo cáo từ module B", deadline="2026-12-20T23:59:00")
    monkeypatch.setattr(account, "current", lambda: ws)
    page = Path(__file__).resolve().parents[2] / "views" / "scheduler.py"
    at = AppTest.from_file(str(page), default_timeout=60).run()
    assert not at.exception
    assert any("Nguồn: 1 nhiệm vụ từ trang Trích xuất (1 đã xác nhận" in c.value for c in at.caption)
