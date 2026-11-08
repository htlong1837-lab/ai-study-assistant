import pytest
from datetime import datetime
from core.contracts import ClassifiedEmail, EmailLabel, Priority, SafetyStatus
from modules.extraction.gate import UnsafeSourceError, ensure_safe
from modules.extraction.schemas import Evidence, ExField, ExtractionResult, RawAssignment, RawDeadline


def test_gate_allows_safe_email():
    email = ClassifiedEmail(
        id="e-safe",
        sender="gv@edu.vn",
        subject="Bai tap",
        body="Noi dung bai tap",
        received_at=datetime(2026, 11, 4, 10, 0),
        label=EmailLabel.ASSIGNMENT,
        safety=SafetyStatus.SAFE,
    )
    # Không raise exception
    ensure_safe(email)


def test_gate_blocks_malicious_email():
    email = ClassifiedEmail(
        id="e-malicious",
        sender="hacker@fake.top",
        subject="Phishing",
        body="Bam vao link doc",
        received_at=datetime(2026, 11, 4, 10, 0),
        label=EmailLabel.PHISHING,
        safety=SafetyStatus.MALICIOUS,
    )
    with pytest.raises(UnsafeSourceError) as exc_info:
        ensure_safe(email)
    assert "Cổng bảo mật chặn" in str(exc_info.value)
    assert "malicious" in str(exc_info.value)


def test_gate_blocks_suspicious_unless_explicitly_allowed():
    email = ClassifiedEmail(
        id="e-suspicious",
        sender="clb@gmail.com",
        subject="Link la",
        body="Tai file tai bit.ly",
        received_at=datetime(2026, 11, 4, 10, 0),
        label=EmailLabel.ANNOUNCEMENT,
        safety=SafetyStatus.SUSPICIOUS,
    )
    # Mặc định chặn
    with pytest.raises(UnsafeSourceError):
        ensure_safe(email, allow_suspicious=False)

    # Khi cho phép chủ động
    ensure_safe(email, allow_suspicious=True)


def test_schemas_nullable_defaults():
    # Kiểm tra schema cho phép toàn bộ trường None mà không ném lỗi
    assignment = RawAssignment()
    assert assignment.title.value is None
    assert assignment.course.value is None
    assert assignment.deadlines == []
    assert assignment.submission_platform.value is None
    assert assignment.submission_format.value is None
    assert assignment.estimated_hours is None
    assert assignment.priority_suggestion is None
    assert assignment.is_extension_notice is False
    assert assignment.refers_to is None

    result = ExtractionResult()
    assert result.assignments == []
    assert result.not_assignment is False


def test_schemas_with_valid_data():
    evidence = Evidence(quote="23h59 thứ 6", location="email")
    deadline = RawDeadline(raw_text="23h59 thứ 6", evidence=evidence)
    assignment = RawAssignment(
        title=ExField(value="Bài tập 1", evidence=evidence),
        course=ExField(value="CS101", evidence=evidence),
        deadlines=[deadline],
        priority_suggestion=Priority.HIGH,
        estimated_hours=5.0
    )
    result = ExtractionResult(assignments=[assignment])

    json_str = result.model_dump_json()
    assert "Bài tập 1" in json_str
    assert "high" in json_str

    parsed = ExtractionResult.model_validate_json(json_str)
    assert parsed.assignments[0].title.value == "Bài tập 1"
    assert parsed.assignments[0].priority_suggestion == Priority.HIGH
