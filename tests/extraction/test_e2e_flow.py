"""Kiểm thử luồng tích hợp đầu - cuối (End-to-End Flow Test) cho Module B.

Kịch bản 4 bước:
1. Tiếp nhận email bài tập an toàn -> LLM trích xuất -> Lưu task vào SQLite ở trạng thái PROPOSED.
2. Sinh viên duyệt và xác nhận -> Task chuyển sang CONFIRMED -> Có thể chuyển sang core.contracts.Task và schedulable().
3. Tiếp nhận email đính chính dời hạn -> Matcher phát hiện trùng bài cũ -> Sinh bản ghi task_update_proposals (không sửa bậy task gốc).
4. Sinh viên chấp nhận đề xuất dời hạn -> Task gốc được cập nhật hạn nộp mới an toàn.
"""
from datetime import datetime
import json
import pytest

from core.contracts import ClassifiedEmail, EmailLabel, SafetyStatus, TaskStatus, schedulable
from db.repository import Repository
from modules.extraction.workflow import (
    accept_update_proposal,
    confirm,
    process_email,
    to_contract_task,
)


class FakeDemoLLMClient:
    """Mock LLM trả lời tương ứng theo nội dung email."""

    def __init__(self):
        self.model = "fake-llm-demo"

    def generate(self, prompt: str, system: str = "", temperature: float = 0.0):
        # Bước 1: Email bài tập gốc (e-step1)
        if "e-step1" in prompt or "Thông báo nộp Báo cáo SP1" in prompt:
            res_dict = {
                "assignments": [
                    {
                        "title": {"value": "Báo cáo SP1", "evidence": {"quote": "Báo cáo SP1", "location": "email"}},
                        "course": {"value": "Trí tuệ nhân tạo", "evidence": {"quote": "Trí tuệ nhân tạo", "location": "email"}},
                        "deadlines": [
                            {
                                "label": "Hạn nộp",
                                "raw_text": "23h59 ngày 13/11/2026",
                                "evidence": {"quote": "23h59 ngày 13/11/2026", "location": "email"},
                            }
                        ],
                        "submission_platform": {"value": "Google Drive", "evidence": {"quote": "Google Drive", "location": "email"}},
                        "submission_format": {"value": [".pdf"], "evidence": {"quote": ".pdf", "location": "email"}},
                        "estimated_hours": 6.0,
                        "priority_suggestion": "high",
                        "is_extension_notice": False,
                    }
                ],
                "not_assignment": False,
            }
        else:
            # Bước 3: Email dời hạn (e-step2)
            res_dict = {
                "assignments": [
                    {
                        "title": {"value": "Báo cáo SP1", "evidence": {"quote": "Báo cáo SP1", "location": "email"}},
                        "course": {"value": "Trí tuệ nhân tạo", "evidence": {"quote": "Trí tuệ nhân tạo", "location": "email"}},
                        "deadlines": [
                            {
                                "label": "Hạn nộp mới",
                                "raw_text": "23h59 ngày 20/11/2026",
                                "evidence": {"quote": "23h59 ngày 20/11/2026", "location": "email"},
                            }
                        ],
                        "submission_platform": {"value": "Google Drive", "evidence": {"quote": "Google Drive", "location": "email"}},
                        "estimated_hours": 6.0,
                        "priority_suggestion": "high",
                        "is_extension_notice": True,
                        "refers_to": "Báo cáo SP1",
                    }
                ],
                "not_assignment": False,
            }

        return type("Resp", (), {
            "text": json.dumps(res_dict, ensure_ascii=False),
            "input_tokens": 120,
            "output_tokens": 80,
            "cached": False,
        })()


@pytest.fixture
def repo(tmp_path):
    return Repository(tmp_path / "e2e_demo.db")


def test_full_demo_lifecycle_scenario(repo):
    llm = FakeDemoLLMClient()

    # ==========================================
    # BƯỚC 1: Xử lý email bài tập gốc ban đầu
    # ==========================================
    email1 = ClassifiedEmail(
        id="e-step1",
        sender="gv.ai@uni.edu.vn",
        subject="[AI] Thông báo nộp Báo cáo SP1",
        body="Các nhóm hoàn thành Báo cáo SP1 môn Trí tuệ nhân tạo trước 23h59 ngày 13/11/2026 lên Google Drive định dạng .pdf.",
        received_at=datetime(2026, 11, 4, 10, 0),
        label=EmailLabel.ASSIGNMENT,
        safety=SafetyStatus.SAFE,
    )

    created_ids = process_email(email1, llm, repo)
    assert len(created_ids) == 1
    task_id = created_ids[0]

    task_in_db = repo.get_task(task_id)
    assert task_in_db["status"] == "proposed"  # Nguyên tắc I: Luôn là proposed
    assert "2026-11-13T23:59:00" in task_in_db["deadline"]
    assert task_in_db["title"] == "Báo cáo SP1"

    # ==========================================
    # BƯỚC 2: Người dùng xác nhận đề xuất
    # ==========================================
    confirmed_task = confirm(task_id, repo)
    assert confirmed_task.status == TaskStatus.CONFIRMED
    assert confirmed_task.deadline == datetime(2026, 11, 13, 23, 59)

    # Chuyển giao sang Module C: schedulable() phải nhận diện task này
    sched_list = schedulable([confirmed_task])
    assert len(sched_list) == 1
    assert sched_list[0].id == task_id

    # ==========================================
    # BƯỚC 3: Tiếp nhận email đính chính dời hạn
    # ==========================================
    email2 = ClassifiedEmail(
        id="e-step2",
        sender="gv.ai@uni.edu.vn",
        subject="[AI] Đính chính dời hạn nộp Báo cáo SP1",
        body="Thầy thông báo dời hạn nộp Báo cáo SP1 môn Trí tuệ nhân tạo đến 23h59 ngày 20/11/2026 lên Google Drive.",
        received_at=datetime(2026, 11, 6, 15, 0),
        label=EmailLabel.ASSIGNMENT,
        safety=SafetyStatus.SAFE,
    )

    updated_ids = process_email(email2, llm, repo)
    assert task_id in updated_ids

    # Quan trọng: Task gốc không bị tự tiện sửa đè!
    task_before_approval = repo.get_task(task_id)
    assert "2026-11-13T23:59:00" in task_before_approval["deadline"]

    # Thay vào đó, một bản ghi proposal được tạo ra ở trạng thái pending
    pending_props = repo.list_pending_proposals(task_id)
    assert len(pending_props) == 1
    prop = pending_props[0]
    assert prop["field"] == "deadline"
    assert "2026-11-13T23:59:00" in prop["old_value"]
    assert "2026-11-20T23:59:00" in prop["new_value"]

    # ==========================================
    # BƯỚC 4: Người dùng chấp nhận dời hạn
    # ==========================================
    updated_task = accept_update_proposal(prop["id"], repo)
    assert updated_task.deadline == datetime(2026, 11, 20, 23, 59)

    # Kiểm tra trong DB task đã được cập nhật sang hạn mới 20/11
    task_after_approval = repo.get_task(task_id)
    assert "2026-11-20T23:59:00" in task_after_approval["deadline"]

    # Không còn proposal nào ở pending
    assert len(repo.list_pending_proposals(task_id)) == 0
