from datetime import datetime
import json
import pytest

from core.contracts import ClassifiedEmail, EmailLabel, Page, ParsedDocument, SafetyStatus
from core.llm_client import LLMClient
from db.repository import Repository
from modules.extraction.extractor import extract_from_document, extract_from_email
from modules.extraction.gate import UnsafeSourceError


class MockLLMClient:
    """Fake LLM client trả về phản hồi định trước cho test."""

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.call_count = 0
        self.model = "fake-model"

    def generate(self, prompt: str, system: str = "", temperature: float = 0.0):
        self.call_count += 1
        return type("Resp", (), {
            "text": self.response_text,
            "input_tokens": 100,
            "output_tokens": 50,
            "cached": False
        })()


@pytest.fixture
def repo(tmp_path):
    return Repository(tmp_path / "test_extractor.db")


def test_extract_blocks_malicious_email():
    email = ClassifiedEmail(
        id="e-phish",
        sender="scam@fake.top",
        subject="Nhận tiền",
        body="Bấm vào link",
        received_at=datetime(2026, 11, 4, 10, 0),
        label=EmailLabel.PHISHING,
        safety=SafetyStatus.MALICIOUS
    )
    llm = MockLLMClient("")
    with pytest.raises(UnsafeSourceError):
        extract_from_email(email, llm)
    assert llm.call_count == 0  # Tuyệt đối không gọi LLM khi bị chặn


def test_extract_from_email_success():
    email = ClassifiedEmail(
        id="e-001",
        sender="gv@uni.edu.vn",
        subject="[AI] Báo cáo SP1",
        body="Các nhóm nộp Báo cáo SP1 môn Trí tuệ nhân tạo trước 23h59 thứ Sáu tuần sau lên hệ thống LMS.",
        received_at=datetime(2026, 11, 4, 10, 0),  # Thứ Tư
        label=EmailLabel.ASSIGNMENT,
        safety=SafetyStatus.SAFE
    )
    mock_json = {
        "assignments": [
            {
                "title": {"value": "Báo cáo SP1", "evidence": {"quote": "Báo cáo SP1", "location": "email"}},
                "course": {"value": "Trí tuệ nhân tạo", "evidence": {"quote": "Trí tuệ nhân tạo", "location": "email"}},
                "deadlines": [
                    {
                        "label": "Hạn nộp",
                        "raw_text": "23h59 thứ Sáu tuần sau",
                        "evidence": {"quote": "23h59 thứ Sáu tuần sau", "location": "email"}
                    }
                ],
                "submission_platform": {"value": "LMS", "evidence": {"quote": "hệ thống LMS", "location": "email"}},
                "submission_format": {"value": None, "evidence": None},
                "naming_convention": {"value": None, "evidence": None},
                "grading_criteria": {"value": None, "evidence": None},
                "estimated_hours": 6.0,
                "priority_suggestion": "high",
                "is_extension_notice": False,
                "refers_to": None
            }
        ],
        "not_assignment": false
    }
    llm = MockLLMClient(json.dumps(mock_json, ensure_ascii=False))
    outcome = extract_from_email(email, llm)

    assert not outcome.is_empty
    assert len(outcome.items) == 1
    item = outcome.items[0]
    assert item.assignment.title.value == "Báo cáo SP1"
    assert item.assignment.course.value == "Trí tuệ nhân tạo"
    assert len(item.normalized_deadlines) == 1
    # 2026-11-04 (Thứ Tư) -> thứ Sáu tuần sau = 2026-11-13 23:59:00
    assert item.normalized_deadlines[0].value.strftime("%Y-%m-%d %H:%M") == "2026-11-13 23:59"
    assert item.confidence >= 0.8
    assert len(item.sources) >= 3


def test_extract_invalid_evidence_revokes_value():
    email = ClassifiedEmail(
        id="e-002",
        sender="gv@uni.edu.vn",
        subject="Bài tập",
        body="Nộp bài tập lớn trước 20/11.",
        received_at=datetime(2026, 11, 4, 10, 0),
        label=EmailLabel.ASSIGNMENT,
        safety=SafetyStatus.SAFE
    )
    # LLM hallucinate ra môn học "Học máy nâng cao" không có trong body
    mock_json = {
        "assignments": [
            {
                "title": {"value": "Bài tập lớn", "evidence": {"quote": "Bài tập lớn", "location": "email"}},
                "course": {"value": "Học máy nâng cao", "evidence": {"quote": "Học máy nâng cao", "location": "email"}},
                "deadlines": [
                    {
                        "raw_text": "20/11",
                        "evidence": {"quote": "20/11", "location": "email"}
                    }
                ]
            }
        ],
        "not_assignment": false
    }
    llm = MockLLMClient(json.dumps(mock_json, ensure_ascii=False))
    outcome = extract_from_email(email, llm)

    item = outcome.items[0]
    assert item.assignment.title.value == "Bài tập lớn"
    # Do "Học máy nâng cao" không có trong email, giá trị phải bị thu hồi thành None
    assert item.assignment.course.value is None
    assert "evidence_not_found:course" in item.warnings


def test_extract_caching_with_repository(repo):
    email = ClassifiedEmail(
        id="e-cached",
        sender="gv@uni.edu.vn",
        subject="Bài tập CSDL",
        body="Nộp bài tập chương 2 trước ngày 15/11/2026.",
        received_at=datetime(2026, 11, 4, 10, 0),
        label=EmailLabel.ASSIGNMENT,
        safety=SafetyStatus.SAFE
    )
    mock_json = {
        "assignments": [
            {
                "title": {"value": "Bài tập chương 2", "evidence": {"quote": "Bài tập chương 2", "location": "email"}},
                "deadlines": [{"raw_text": "15/11/2026", "evidence": {"quote": "15/11/2026", "location": "email"}}]
            }
        ],
        "not_assignment": false
    }
    llm = MockLLMClient(json.dumps(mock_json, ensure_ascii=False))

    # Lần 1: Gọi LLM thật (mock) và ghi vào DB
    outcome1 = extract_from_email(email, llm, repo=repo)
    assert not outcome1.from_cache
    assert llm.call_count == 1

    # Lần 2: Cùng email, cùng nội dung -> Phải lấy từ Cache
    outcome2 = extract_from_email(email, llm, repo=repo)
    assert outcome2.from_cache
    assert llm.call_count == 1  # Không tăng số lần gọi


def test_extract_empty_when_not_assignment():
    email = ClassifiedEmail(
        id="e-schedule",
        sender="phongdaotao@uni.edu.vn",
        subject="Đổi phòng học",
        body="Lớp học chuyển sang phòng B102.",
        received_at=datetime(2026, 11, 4, 10, 0),
        label=EmailLabel.SCHEDULE,
        safety=SafetyStatus.SAFE
    )
    mock_json = {"assignments": [], "not_assignment": true}
    llm = MockLLMClient(json.dumps(mock_json))
    outcome = extract_from_email(email, llm)
    assert outcome.is_empty
    assert len(outcome.items) == 0


def test_extract_from_document_success():
    doc = ParsedDocument(
        doc_id="d-001",
        filename="de_bai.pdf",
        pages=[
            Page(1, "TRƯỜNG ĐẠI HỌC BÁCH KHOA\nĐỀ BÀI TẬP LỚN MÔN TRÍ TUỆ NHÂN TẠO"),
            Page(2, "Yêu cầu: Nộp báo cáo SP1 trước 23h59 ngày 20/11/2026 lên hệ thống."),
        ]
    )
    mock_json = {
        "assignments": [
            {
                "title": {"value": "Đề bài tập lớn", "evidence": {"quote": "ĐỀ BÀI TẬP LỚN", "location": "p1"}},
                "course": {"value": "Trí tuệ nhân tạo", "evidence": {"quote": "TRÍ TUỆ NHÂN TẠO", "location": "p1"}},
                "deadlines": [
                    {
                        "raw_text": "23h59 ngày 20/11/2026",
                        "evidence": {"quote": "23h59 ngày 20/11/2026", "location": "p2"}
                    }
                ]
            }
        ],
        "not_assignment": false
    }
    llm = MockLLMClient(json.dumps(mock_json, ensure_ascii=False))
    outcome = extract_from_document(doc, llm, anchor=datetime(2026, 11, 4, 10, 0))

    assert not outcome.is_empty
    assert len(outcome.items) == 1
    item = outcome.items[0]
    assert item.assignment.title.value == "Đề bài tập lớn"
    assert item.normalized_deadlines[0].value.strftime("%Y-%m-%d %H:%M") == "2026-11-20 23:59"
    # Kiểm tra source location có p1, p2
    doc_sources = [s["source"] for s in item.sources]
    assert "doc:d-001#p1" in doc_sources
    assert "doc:d-001#p2" in doc_sources or "doc:d-001" in doc_sources
