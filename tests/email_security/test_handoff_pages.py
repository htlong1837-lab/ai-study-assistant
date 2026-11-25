import hashlib
from datetime import datetime, timezone
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core.contracts import (
    ClassifiedEmail,
    EmailLabel,
    Page,
    ParsedDocument,
    SafeAttachment,
    SafetyStatus,
)

ROOT = Path(__file__).resolve().parents[2]


def test_extraction_page_reads_approved_suspicious_email(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    email = ClassifiedEmail(
        id="page-handoff-suspicious",
        sender="teacher@uni.edu.vn",
        subject="Bài tập đã duyệt từ D",
        body="Nộp bài trước thứ Sáu.",
        received_at=datetime.now(timezone.utc),
        label=EmailLabel.ASSIGNMENT,
        safety=SafetyStatus.SUSPICIOUS,
        label_confidence=0.9,
    )
    app = AppTest.from_file(
        str(ROOT / "views" / "extraction.py"), default_timeout=30
    ).run()
    app.session_state["verified_emails"] = {email.id: email}
    app.session_state["approved_suspicious_email_ids"] = {email.id}
    app.run()

    assert not app.exception
    rendered = [item.value for item in (*app.markdown, *app.warning, *app.success)]
    assert any(email.subject in value for value in rendered)
    assert any("NGHI NGỜ – ĐÃ DUYỆT" in value for value in rendered)


def test_qa_page_offers_only_safe_attachment_handoff(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    path = tmp_path / "assignment.txt"
    path.write_text("Deadline bài tập là thứ Sáu.", encoding="utf-8")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    attachment = SafeAttachment(path=str(path), sha256=sha, email_id="page-handoff-safe")
    document = ParsedDocument(
        doc_id=sha,
        filename=path.name,
        pages=[Page(number=1, text="Deadline bài tập là thứ Sáu.")],
    )
    app = AppTest.from_file(str(ROOT / "views" / "qa.py"), default_timeout=30).run()
    app.session_state["safe_attachments"] = {attachment.sha256: attachment}
    app.session_state["verified_documents"] = {attachment.sha256: document}
    app.run()
    assert all("từ email" in option for option in app.selectbox[0].options)
    assert not app.file_uploader  # không cho tải thẳng, chỉ nhận tệp qua D

    assert not app.exception
    assert app.session_state["qa_document"].doc_id == document.doc_id
    assert any("đã qua kiểm tra an toàn" in item.value for item in app.success)


def test_qa_page_rejects_attachment_changed_after_scan(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    path = tmp_path / "assignment.txt"
    path.write_text("Nội dung gốc.", encoding="utf-8")
    attachment = SafeAttachment(path=str(path), sha256="c" * 64, email_id="tampered")
    document = ParsedDocument(doc_id="c" * 64, filename=path.name,
                              pages=[Page(number=1, text="Nội dung gốc.")])
    app = AppTest.from_file(str(ROOT / "views" / "qa.py"), default_timeout=30)
    app.session_state["safe_attachments"] = {attachment.sha256: attachment}
    app.session_state["verified_documents"] = {attachment.sha256: document}
    app.run()
    assert not app.exception
    assert "qa_document" not in app.session_state
    assert any("SHA-256 không khớp" in item.value for item in app.error)
