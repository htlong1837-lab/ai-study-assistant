from datetime import datetime, timedelta

import pytest

from core.contracts import (
    ClassifiedEmail, EmailLabel, Page, ParsedDocument, Priority, Reminder, ReminderChannel,
    SafeAttachment, SafetyStatus, StudyBlock, Task, TaskStatus, can_forward, schedulable,
)

NOW = datetime(2026, 11, 9, 8, 0)


def make_email(safety=SafetyStatus.SAFE, **kw):
    data = dict(id="e1", sender="gv@uni.edu.vn", subject="BTL", body="Nộp bài",
                received_at=NOW, label=EmailLabel.ASSIGNMENT, safety=safety)
    data.update(kw)
    return ClassifiedEmail(**data)


def make_task(**kw):
    data = dict(id="t1", title="Báo cáo SP1", course="AI", deadline=NOW + timedelta(days=5),
                estimated_hours=4, source="email:e1", confidence=0.9)
    data.update(kw)
    return Task(**data)


# --- ClassifiedEmail và cổng chặn ---

def test_email_valid():
    assert make_email().label is EmailLabel.ASSIGNMENT


def test_email_accepts_string_enums():
    e = make_email(safety="suspicious", label="phishing")
    assert e.safety is SafetyStatus.SUSPICIOUS and e.label is EmailLabel.PHISHING


@pytest.mark.parametrize("bad", [{"id": ""}, {"label_confidence": 1.5}, {"safety": "unknown"}])
def test_email_invalid(bad):
    with pytest.raises(ValueError):
        make_email(**bad)


def test_gate_blocks_malicious_always():
    e = make_email(SafetyStatus.MALICIOUS)
    assert can_forward(e) is False
    assert can_forward(e, allow_suspicious=True) is False


def test_gate_suspicious_needs_permission():
    e = make_email(SafetyStatus.SUSPICIOUS)
    assert can_forward(e) is False
    assert can_forward(e, allow_suspicious=True) is True


def test_gate_safe_passes():
    assert can_forward(make_email()) is True


# --- SafeAttachment, ParsedDocument ---

def test_attachment_hash_must_be_sha256():
    SafeAttachment(path="a.pdf", sha256="a" * 64, email_id="e1")
    with pytest.raises(ValueError):
        SafeAttachment(path="a.pdf", sha256="xyz", email_id="e1")


def test_document_pages():
    doc = ParsedDocument(doc_id="d1", filename="de.pdf",
                         pages=[Page(1, "Mở đầu"), Page(2, "Hạn nộp 23h59")])
    assert doc.text_of([2]) == "Hạn nộp 23h59"
    with pytest.raises(ValueError):
        Page(0, "x")
    with pytest.raises(ValueError):
        ParsedDocument(doc_id="d1", filename="de.pdf", pages=[Page(1, "a"), Page(1, "b")])


# --- Task ---

def test_task_defaults_to_proposed():
    t = make_task()
    assert t.status is TaskStatus.PROPOSED and t.priority is Priority.MEDIUM


@pytest.mark.parametrize("bad", [{"title": " "}, {"estimated_hours": 0},
                                 {"confidence": -0.1}, {"deadline": None}])
def test_task_invalid(bad):
    with pytest.raises(ValueError):
        make_task(**bad)


def test_task_transitions():
    t = make_task()
    t.confirm()
    assert t.status is TaskStatus.CONFIRMED
    t.cancel()
    assert t.status is TaskStatus.CANCELLED
    with pytest.raises(ValueError):
        t.confirm()


def test_schedulable_only_confirmed():
    a, b, c = make_task(id="a"), make_task(id="b"), make_task(id="c")
    b.confirm()
    c.cancel()
    assert [t.id for t in schedulable([a, b, c])] == ["b"]


# --- StudyBlock, Reminder ---

def test_study_block():
    blk = StudyBlock(task_id="t1", start=NOW, end=NOW + timedelta(minutes=90))
    assert blk.hours == 1.5
    with pytest.raises(ValueError):
        StudyBlock(task_id="t1", start=NOW, end=NOW)


def test_reminder():
    r = Reminder(task_id="t1", remind_at=NOW, channel="telegram", message="Học AI")
    assert r.channel is ReminderChannel.TELEGRAM
    with pytest.raises(ValueError):
        Reminder(task_id="t1", remind_at=NOW, channel="sms", message="x")
