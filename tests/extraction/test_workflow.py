from datetime import datetime
import json
import pytest

from core.contracts import ClassifiedEmail, EmailLabel, SafetyStatus, TaskStatus
from db.repository import Repository
from modules.extraction.workflow import (
    accept_update_proposal,
    cancel,
    confirm,
    process_email,
    reject_update_proposal,
    resolve_conflict,
    to_contract_task,
)


class MockLLMClient:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.model = "fake-model"

    def generate(self, prompt: str, system: str = "", temperature: float = 0.0):
        return type("Resp", (), {
            "text": self.response_text,
            "input_tokens": 100,
            "output_tokens": 50,
            "cached": False,
        })()


@pytest.fixture
def repo(tmp_path):
    return Repository(tmp_path / "test_workflow.db")


def test_proposed_to_confirmed_lifecycle(repo):
    task_id = repo.create_task({
        "id": "t-001",
        "title": "Báo cáo SP1",
        "course": "Trí tuệ nhân tạo",
        "deadline": "2026-11-20T23:59:00",
        "estimated_hours": 4.0,
        "priority": "high",
        "status": "proposed",
    })

    # Ban đầu là proposed
    row = repo.get_task(task_id)
    assert row["status"] == "proposed"

    # Người dùng xác nhận -> chuyển sang confirmed
    c_task = confirm(task_id, repo)
    assert c_task.status == TaskStatus.CONFIRMED
    assert c_task.title == "Báo cáo SP1"
    assert c_task.deadline == datetime(2026, 11, 20, 23, 59)

    # Kiểm tra trong DB
    updated = repo.get_task(task_id)
    assert updated["status"] == "confirmed"
    assert updated["confirmed_at"] is not None


def test_proposed_to_cancelled_lifecycle(repo):
    task_id = repo.create_task({
        "id": "t-002",
        "title": "Bài tập không liên quan",
        "status": "proposed",
    })

    cancel(task_id, repo)
    row = repo.get_task(task_id)
    assert row["status"] == "cancelled"

    # Huỷ lại một task đã cancelled sẽ báo lỗi
    with pytest.raises(ValueError, match="đã ở trạng thái 'cancelled'"):
        cancel(task_id, repo)


def test_cancelled_to_confirmed_forbidden(repo):
    task_id = repo.create_task({
        "id": "t-003",
        "title": "Bài tập đã huỷ",
        "deadline": "2026-11-20T23:59:00",
        "status": "cancelled",
    })

    with pytest.raises(ValueError, match="không thể chuyển trực tiếp sang 'confirmed'"):
        confirm(task_id, repo)


def test_confirm_blocked_when_no_deadline(repo):
    task_id = repo.create_task({
        "id": "t-004",
        "title": "Bài tập chưa có hạn",
        "deadline": None,
        "status": "proposed",
    })

    # Không có deadline -> bị chặn
    with pytest.raises(ValueError, match="chưa có hạn nộp"):
        confirm(task_id, repo)

    # Nếu người dùng bổ sung deadline qua overrides -> thành công
    c_task = confirm(task_id, repo, overrides={"deadline": datetime(2026, 11, 25, 23, 59)})
    assert c_task.status == TaskStatus.CONFIRMED
    assert c_task.deadline == datetime(2026, 11, 25, 23, 59)


def test_confirm_blocked_when_unresolved_conflicts(repo):
    task_id = repo.create_task({
        "id": "t-005",
        "title": "Bài tập có mâu thuẫn",
        "deadline": "2026-11-20T23:59:00",
        "status": "proposed",
    })

    # Thêm mâu thuẫn chưa giải quyết
    conflict_id = repo.add_conflict({
        "task_id": task_id,
        "kind": "deadline",
        "value_a": "2026-11-20T23:59:00",
        "value_b": "2026-11-27T23:59:00",
    })

    # Chặn xác nhận khi conflict chưa giải quyết
    with pytest.raises(ValueError, match="mâu thuẫn chưa giải quyết"):
        confirm(task_id, repo)

    # Giải quyết mâu thuẫn
    resolve_conflict(conflict_id, choice="b", repo=repo)

    # Sau khi giải quyết -> xác nhận thành công
    c_task = confirm(task_id, repo)
    assert c_task.status == TaskStatus.CONFIRMED


def test_update_proposal_flow(repo):
    task_id = repo.create_task({
        "id": "t-006",
        "title": "Báo cáo giữa kỳ",
        "deadline": "2026-11-15T23:59:00",
        "status": "confirmed",
    })

    # Sinh đề xuất dời hạn
    proposal_id = repo.add_update_proposal({
        "task_id": task_id,
        "field": "deadline",
        "old_value": "2026-11-15T23:59:00",
        "new_value": "2026-11-22T23:59:00",
        "source": "email:e-ext",
        "status": "pending",
    })

    # 1. Chấp thuận proposal
    updated_task = accept_update_proposal(proposal_id, repo)
    assert updated_task.deadline == datetime(2026, 11, 22, 23, 59)

    # Kiểm tra trong DB task đã được cập nhật
    task_row = repo.get_task(task_id)
    assert task_row["deadline"] == "2026-11-22T23:59:00"

    # 2. Sinh đề xuất khác rồi từ chối
    prop2_id = repo.add_update_proposal({
        "task_id": task_id,
        "field": "deadline",
        "old_value": "2026-11-22T23:59:00",
        "new_value": "2026-11-30T23:59:00",
        "source": "email:e-spam",
        "status": "pending",
    })
    reject_update_proposal(prop2_id, repo)
    # Deadline vẫn giữ nguyên 22/11
    assert repo.get_task(task_id)["deadline"] == "2026-11-22T23:59:00"


def test_process_email_creates_proposed_task(repo):
    email = ClassifiedEmail(
        id="e-test-1",
        sender="teacher@uni.edu.vn",
        subject="[AI] Bài tập lớn",
        body="Nộp Báo cáo SP1 môn Trí tuệ nhân tạo trước 23h59 ngày 20/11/2026 lên hệ thống LMS.",
        received_at=datetime(2026, 11, 4, 8, 0),
        label=EmailLabel.ASSIGNMENT,
        safety=SafetyStatus.SAFE,
    )
    mock_json = {
        "assignments": [
            {
                "title": {"value": "Báo cáo SP1", "evidence": {"quote": "Báo cáo SP1", "location": "email"}},
                "course": {"value": "Trí tuệ nhân tạo", "evidence": {"quote": "Trí tuệ nhân tạo", "location": "email"}},
                "deadlines": [
                    {
                        "raw_text": "23h59 ngày 20/11/2026",
                        "evidence": {"quote": "23h59 ngày 20/11/2026", "location": "email"},
                    }
                ],
                "submission_platform": {"value": "LMS", "evidence": {"quote": "hệ thống LMS", "location": "email"}},
                "estimated_hours": 5.0,
                "priority_suggestion": "high",
            }
        ],
        "not_assignment": False,
    }
    llm = MockLLMClient(json.dumps(mock_json, ensure_ascii=False))

    task_ids = process_email(email, llm, repo)
    assert len(task_ids) == 1
    task_id = task_ids[0]

    # Kiểm tra lưu vào DB ở trạng thái proposed
    task_row = repo.get_task(task_id)
    assert task_row["status"] == "proposed"
    assert task_row["title"] == "Báo cáo SP1"
    assert task_row["course"] == "Trí tuệ nhân tạo"
    assert task_row["estimated_hours"] == 5.0
    assert task_row["priority"] == "high"

    # Kiểm tra assignment_details được lưu
    details = repo.get_assignment_details(task_id)
    assert details is not None
    assert details["submission_platform"] == "LMS"
    assert details["raw_deadline_text"] == "23h59 ngày 20/11/2026"
