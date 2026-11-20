from datetime import datetime, timezone

from core.contracts import (
    ClassifiedEmail,
    EmailLabel,
    SafeAttachment,
    SafetyStatus,
)
from modules.email_security.handoff import publish_to_modules
from modules.email_security.models import ProcessedEmail


def _processed(safety: SafetyStatus, approved: bool, path: str = "") -> ProcessedEmail:
    email = ClassifiedEmail(
        id="handoff-test",
        sender="teacher@uni.edu.vn",
        subject="Bài tập",
        body="Nộp bài.",
        received_at=datetime.now(timezone.utc),
        label=EmailLabel.ASSIGNMENT,
        safety=safety,
        label_confidence=0.9,
    )
    attachments = (
        [SafeAttachment(path=path, sha256="a" * 64, email_id=email.id)] if path else []
    )
    return ProcessedEmail(
        email=email,
        safe_attachments=attachments,
        url_findings=[],
        attachment_findings=[],
        sender_reasons=[],
        classifier_method="tfidf",
        can_forward=safety is SafetyStatus.SAFE or approved,
        user_approved=approved,
    )


def test_safe_email_and_gated_document_are_published(tmp_path):
    file = tmp_path / "assignment.txt"
    file.write_text("Deadline: Friday", encoding="utf-8")
    result = _processed(SafetyStatus.SAFE, approved=False, path=str(file))
    state = {}

    assert publish_to_modules(result, state)
    assert state["verified_emails"][result.email.id] is result.email
    assert result.email.id in state["verified_email_ids"]
    assert "a" * 64 in state["safe_attachments"]
    assert state["verified_documents"]["a" * 64].pages[0].text == "Deadline: Friday"


def test_approved_suspicious_email_is_published_with_approval_marker():
    result = _processed(SafetyStatus.SUSPICIOUS, approved=True)
    state = {}

    assert publish_to_modules(result, state)
    assert result.email.id in state["approved_suspicious_email_ids"]


def test_malicious_email_never_reaches_b_or_a():
    result = _processed(SafetyStatus.MALICIOUS, approved=True)
    state = {}

    assert not publish_to_modules(result, state)
    assert state == {}


def test_unapproved_suspicious_email_is_not_published():
    result = _processed(SafetyStatus.SUSPICIOUS, approved=False)
    state = {}

    assert not publish_to_modules(result, state)
    assert state == {}
