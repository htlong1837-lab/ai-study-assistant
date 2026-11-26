import pytest

from core import workspace
from modules.email_security import purpose
from modules.email_security.handoff import verified_document_batches
from modules.extraction.intake import intake_from_d


@pytest.mark.parametrize("name,text,expect", [
    ("Lich_thi_HK1.xlsx", "", "exam"),
    ("TKB_K66.png", "", "timetable"),
    ("de_bai_BTL2.pdf", "", "assignment"),
    ("slide_chuong3.pptx", "", "material"),
    ("thong_bao.pdf", "Thông báo lịch thi cuối kỳ", "exam"),
    ("anh.jpg", "", "material"),
])
def test_suggest(name, text, expect):
    assert purpose.suggest(name, text) == expect


def test_decisions_persist_and_gate_pages(tmp_path):
    ws = workspace.for_user("sv@gmail.com", base=tmp_path)
    state = {}
    purpose.remember(ws, state, "a" * 64, "assignment")
    purpose.remember(ws, state, "b" * 64, "material")
    purpose.remember(ws, state, "c" * 64, "exam")
    assert purpose.decisions(ws)["c" * 64] == {"purpose": "exam", "done": True}
    assert purpose.allows(state, "a" * 64, "extraction") and purpose.allows(state, "a" * 64, "qa")
    assert not purpose.allows(state, "b" * 64, "extraction") and purpose.allows(state, "b" * 64, "qa")
    assert not purpose.allows(state, "c" * 64, "qa")
    assert not purpose.allows(state, "d" * 64, "extraction")  # chưa duyệt
    fresh = {}
    purpose.sync(ws, fresh)  # phiên mới đọc lại từ tài khoản
    assert fresh == state
    assert purpose.allows({}, "d" * 64, "qa")  # phiên chưa mở Hộp thư: giữ cách cũ


class _Att:
    def __init__(self, sha):
        self.sha256, self.email_id = sha, "e1"


class _Doc:
    def __init__(self, i):
        self.doc_id = i


def test_only_approved_files_reach_extraction_and_qa():
    a, b = "a" * 64, "b" * 64
    state = {"safe_attachments": {a: _Att(a), b: _Att(b)}, "verified_documents": {a: _Doc("da"), b: _Doc("db")},
             purpose.STATE_KEY: {a: "assignment", b: "material"}}
    intake = intake_from_d(state, list, list)
    assert [d.doc_id for d in intake.documents] == ["da"]
    assert [d.doc_id for _, d in verified_document_batches(state)] == ["da", "db"]
