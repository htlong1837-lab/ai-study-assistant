"""Cạnh nối D → B: trang Trích xuất nhận email/tài liệu D đã chuyển qua session_state."""
from datetime import datetime
from pathlib import Path

import pytest

from core import mocks
from core.contracts import ClassifiedEmail, EmailLabel, SafetyStatus
from core.llm_client import LLMClient
from db.repository import Repository
from modules.email_security.handoff import publish_to_modules
from modules.email_security.models import ProcessedEmail
from modules.extraction import workflow
from modules.extraction.gate import UnsafeSourceError
from modules.extraction.intake import intake_from_d


def _email(eid, safety):
    return ClassifiedEmail(
        id=eid, sender="gv@uni.edu.vn", subject=f"Bài tập {eid}",
        body="Nộp báo cáo môn AI trước 23h59 ngày 28/11/2026.",
        received_at=datetime(2026, 11, 20, 8, 0), label=EmailLabel.ASSIGNMENT, safety=safety,
    )


def test_falls_back_to_mocks_when_d_sent_nothing():
    intake = intake_from_d({}, mocks.emails, mocks.documents)
    assert not intake.from_d
    assert [e.id for e in intake.emails] == [e.id for e in mocks.emails()]
    assert len(intake.documents) == len(mocks.documents())


def test_uses_d_emails_and_marks_approved_suspicious():
    state = {
        "verified_emails": {"e-1": _email("e-1", SafetyStatus.SAFE),
                            "e-2": _email("e-2", SafetyStatus.SUSPICIOUS)},
        "approved_suspicious_email_ids": {"e-2"},
    }
    intake = intake_from_d(state, mocks.emails, mocks.documents)
    assert intake.from_d
    assert [e.id for e in intake.emails] == ["e-1", "e-2"]
    assert intake.documents == []  # không lẫn tài liệu mẫu vào dữ liệu thật
    assert [intake.allow_suspicious(e) for e in intake.emails] == [False, True]


def test_real_d_handoff_reaches_b_and_b_gate_respects_approval(tmp_path):
    """Đi trọn đường: D publish_to_modules → intake → workflow.process_email của B."""
    suspicious = _email("e-9", SafetyStatus.SUSPICIOUS)
    processed = ProcessedEmail(
        email=suspicious, safe_attachments=[], url_findings=[], attachment_findings=[],
        sender_reasons=[], classifier_method="tfidf", can_forward=False, user_approved=True,
    )
    state: dict = {}
    assert publish_to_modules(processed, state)

    intake = intake_from_d(state, mocks.emails, mocks.documents)
    (email,) = intake.emails
    repo = Repository(tmp_path / "b.db")
    llm = LLMClient(provider="fake", model="fake-model")

    with pytest.raises(UnsafeSourceError):  # thiếu cờ duyệt → B vẫn chặn
        workflow.process_email(email, llm, repo)
    workflow.process_email(email, llm, repo, allow_suspicious=intake.allow_suspicious(email))


def test_extraction_page_shows_d_emails():
    from streamlit.testing.v1 import AppTest

    page = Path(__file__).resolve().parents[2] / "views" / "extraction.py"
    at = AppTest.from_file(str(page), default_timeout=60)
    at.session_state["verified_emails"] = {"e-7": _email("e-7", SafetyStatus.SUSPICIOUS)}
    at.session_state["approved_suspicious_email_ids"] = {"e-7"}
    at.run()
    assert not at.exception
    assert any("1 email đã duyệt" in c.value for c in at.caption)
    assert any("NGHI NGỜ – ĐÃ DUYỆT" in w.value for w in at.warning)
