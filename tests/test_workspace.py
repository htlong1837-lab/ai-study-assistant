import os
import time
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core import workspace
from core.workspace import Workspace
from db.repository import Repository

ROOT = Path(__file__).resolve().parents[1]


def _task(repo: Repository, tid: str, title: str) -> None:
    repo.create_task({"id": tid, "title": title, "course": "CSDL", "deadline": "2026-12-20T23:59:00",
                      "estimated_hours": 3.0, "priority": "medium", "confidence": 0.9,
                      "status": "confirmed", "created_at": "2026-11-25T08:00:00+00:00"})


def test_each_account_has_its_own_folder(tmp_path):
    a = workspace.for_user("SV.A@Gmail.com ", base=tmp_path)
    a2 = workspace.for_user("sv.a@gmail.com", base=tmp_path)
    b = workspace.for_user("sv.b@gmail.com", base=tmp_path)
    assert a.root == a2.root != b.root
    assert "gmail" not in a.root.name and a.root.is_dir()  # tên thư mục không lộ email
    assert a.db_path.parent == a.root and not a.is_guest
    with pytest.raises(ValueError):
        workspace.for_user("", base=tmp_path)


def test_guest_folder_is_per_session_and_cleaned(tmp_path):
    g1 = workspace.for_guest("abc-123", base=tmp_path)
    g2 = workspace.for_guest("../../etc", base=tmp_path)
    assert g1.is_guest and g1.root.parent == tmp_path and g2.root.parent == tmp_path
    old = time.time() - 3 * 24 * 3600
    os.utime(g1.root, (old, old))
    assert workspace.cleanup_guests(base=tmp_path) == 1
    assert not g1.root.exists() and g2.root.exists()


def test_timetable_saved_per_account(tmp_path):
    ws = workspace.for_user("sv@gmail.com", base=tmp_path)
    assert not ws.has_own_timetable() and ws.timetable_source().name == "thoi_khoa_bieu.csv"
    ws.save_timetable(b"thu,bat_dau,ket_thuc,mon,phong\n2,07:00,09:00,CSDL,A1\n")
    assert ws.timetable_source() == ws.timetable_path
    ws.reset_timetable()
    assert not ws.has_own_timetable()


def _scheduler_as(monkeypatch, ws: Workspace) -> AppTest:
    import views._account as account
    monkeypatch.setattr(account, "current", lambda: ws)
    return AppTest.from_file(str(ROOT / "views" / "scheduler.py"), default_timeout=60).run()


def test_accounts_do_not_see_each_others_tasks(tmp_path, monkeypatch):
    a = workspace.for_user("a@gmail.com", base=tmp_path)
    b = workspace.for_user("b@gmail.com", base=tmp_path)
    _task(Repository(a.db_path), "t-a", "Việc riêng của A")

    at = _scheduler_as(monkeypatch, a)
    assert not at.exception, at.exception
    assert "Việc riêng của A" in list(at.dataframe[0].value["Nhiệm vụ"])

    at = _scheduler_as(monkeypatch, b)
    assert not at.exception, at.exception
    assert any("chưa có nhiệm vụ nào" in i.value for i in at.info)  # B không thấy việc của A
    assert not any("dữ liệu mẫu" in c.value for c in at.caption)  # và không bị lẫn dữ liệu mẫu


def test_guest_gets_sample_tasks_but_account_does_not(tmp_path, monkeypatch):
    import views._account as account
    monkeypatch.setattr(account.workspace, "GUESTS_DIR", tmp_path / "guests")
    monkeypatch.setattr(account.workspace, "USERS_DIR", tmp_path / "users")
    at = AppTest.from_file(str(ROOT / "views" / "home.py"), default_timeout=60).run()
    assert not at.exception, at.exception
    (guest_db,) = (tmp_path / "guests").glob("*/app.db")
    assert Repository(guest_db).list_tasks()  # khách có dữ liệu mẫu để dùng thử
    assert not (tmp_path / "users").exists()
