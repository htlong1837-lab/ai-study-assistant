"""Cùng một tài khoản: rời trang, tải lại hay mở phiên mới thì dữ liệu vẫn còn."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import workspace
from db.repository import Repository
from views import _inbox

ROOT = Path(__file__).resolve().parents[1]
DEMO = sorted((ROOT / "data" / "demo").glob("*.eml"))


def _as(monkeypatch, ws):
    import views._account as account
    monkeypatch.setattr(account, "current", lambda: ws)
    monkeypatch.setenv("LLM_PROVIDER", "fake")


def test_inbox_and_decisions_survive_a_new_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    ws = workspace.for_user("sv@gmail.com", base=tmp_path)
    s1: dict = {}
    from modules.email_security.handoff import publish_to_modules

    s1["_raw_of"] = {}
    items = []
    for path in DEMO:
        raw = path.read_bytes()
        p = _inbox.process(ws, raw)
        s1["_raw_of"][p.email.id] = _inbox.save_raw(ws, raw)
        items.append(p)
    forwarded = [p for p in items if p.can_forward][:2]
    for p in forwarded:
        assert publish_to_modules(p, s1)
        _inbox.remember(ws, s1, p.email.id, "forwarded")

    s2: dict = {}  # phiên mới, ví dụ tải lại trang hoặc mở trên máy khác
    assert _inbox.restore(ws, s2) == len(DEMO)
    assert {p.email.subject for p in s2["processed_list"]} == {p.email.subject for p in items}
    assert {e.subject for e in s2["verified_emails"].values()} == {p.email.subject for p in forwarded}
    assert s2["safe_attachments"]  # tệp đính kèm của email đã chuyển cũng có lại cho trang Hỏi đáp


def test_extraction_page_sees_forwarded_email_after_reload(tmp_path, monkeypatch):
    ws = workspace.for_user("sv@gmail.com", base=tmp_path)
    s: dict = {"_raw_of": {}}
    raw = (ROOT / "data" / "demo" / "02_doi_han.eml").read_bytes()
    p = _inbox.process(ws, raw)
    s["_raw_of"][p.email.id] = _inbox.save_raw(ws, raw)
    _inbox.remember(ws, s, p.email.id, "forwarded")

    _as(monkeypatch, ws)
    import views._account as account
    real_restore = _inbox.restore
    monkeypatch.setattr(account, "current", lambda: (real_restore(ws, __import__("streamlit").session_state), ws)[1])
    at = AppTest.from_file(str(ROOT / "views" / "extraction.py"), default_timeout=60).run()
    assert not at.exception, at.exception
    shown = [m.value for m in (*at.success, *at.warning, *at.markdown)]
    assert any("Dời hạn bài tập lớn số 2" in v for v in shown), shown


def test_schedule_settings_and_confirmations_are_kept(tmp_path, monkeypatch):
    ws = workspace.for_user("sv@gmail.com", base=tmp_path)
    Repository(ws.db_path).create_task({
        "id": "t-1", "title": "Đồ án CSDL", "course": "CSDL", "deadline": "2026-12-20T23:59:00",
        "estimated_hours": 3.0, "priority": "medium", "confidence": 0.9, "status": "proposed",
        "created_at": "2026-11-25T08:00:00+00:00"})
    ws.write_state("schedule", {"days": 14, "day_start": "08:00", "day_end": "21:00", "max_h": 3.0,
                                "mode": "EDF", "min_block": 90, "ran": True})
    _as(monkeypatch, ws)
    at = AppTest.from_file(str(ROOT / "views" / "scheduler.py"), default_timeout=60).run()
    assert not at.exception, at.exception
    assert at.slider[0].value == 14 and at.selectbox[0].value == 90 and at.radio[0].value == "EDF"

    # Tích "Xác nhận" trong bảng nhiệm vụ → ghi vào CSDL của tài khoản
    at.session_state["task_editor"] = {"edited_rows": {0: {"Xác nhận": True}}, "added_rows": [], "deleted_rows": []}
    at.run()
    assert not at.exception, at.exception
    assert Repository(ws.db_path).get_task("t-1")["status"] == "confirmed"
    assert "sched" in at.session_state  # đã từng xếp: mở lại tự xếp theo cài đặt đã lưu
