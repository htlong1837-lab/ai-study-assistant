import sqlite3
import pytest
from db.repository import Repository, init_db


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_assistant.db"
    return Repository(db_file)


def test_init_db_idempotent(tmp_path):
    db_file = tmp_path / "idempotent.db"
    init_db(db_file)
    init_db(db_file)  # Gọi lần 2 không gây lỗi
    assert db_file.exists()


def test_task_crud_with_null_deadline(repo):
    task_id = repo.create_task({
        "id": "t-001",
        "title": "Báo cáo giữa kỳ AI",
        "course": "Trí tuệ nhân tạo",
        "deadline": None,  # Cho phép NULL khi proposed
        "estimated_hours": 6.0,
        "priority": "high",
        "confidence": 0.95,
        "status": "proposed"
    })
    assert task_id == "t-001"

    task = repo.get_task("t-001")
    assert task is not None
    assert task["title"] == "Báo cáo giữa kỳ AI"
    assert task["deadline"] is None
    assert task["status"] == "proposed"

    # Cập nhật deadline và chuyển trạng thái
    repo.update_task_fields("t-001", deadline="2026-11-20T23:59:00+07:00")
    repo.set_task_status("t-001", "confirmed", confirmed_at="2026-11-08T12:00:00+07:00")

    updated = repo.get_task("t-001")
    assert updated["deadline"] == "2026-11-20T23:59:00+07:00"
    assert updated["status"] == "confirmed"
    assert updated["confirmed_at"] == "2026-11-08T12:00:00+07:00"

    # Lọc danh sách theo status
    confirmed_tasks = repo.list_tasks(status="confirmed")
    assert len(confirmed_tasks) == 1
    assert confirmed_tasks[0]["id"] == "t-001"

    proposed_tasks = repo.list_tasks(status="proposed")
    assert len(proposed_tasks) == 0


def test_cascade_delete(repo):
    repo.create_task({"id": "t-cascade", "title": "Task Test Cascade", "status": "proposed"})
    repo.add_sources("t-cascade", [{"source": "email:e-01", "field": "title", "quote": "Task Test Cascade", "kind": "email"}])
    repo.save_assignment_details("t-cascade", {
        "raw_deadline_text": "23h59 thứ Sáu",
        "submission_format": [".pdf"],
        "grading_criteria": ["Đúng format (50%)", "Nội dung (50%)"]
    })
    repo.add_conflict({
        "task_id": "t-cascade",
        "kind": "deadline",
        "value_a": "18/11",
        "value_b": "25/11",
        "suggestion": "b"
    })
    repo.add_update_proposal({
        "task_id": "t-cascade",
        "field": "deadline",
        "old_value": "18/11",
        "new_value": "25/11",
        "source": "email:e-02"
    })

    # Kiểm tra dữ liệu con đã tồn tại
    assert len(repo.get_sources("t-cascade")) == 1
    assert repo.get_assignment_details("t-cascade") is not None
    assert len(repo.list_conflicts("t-cascade")) == 1
    assert len(repo.list_pending_proposals("t-cascade")) == 1

    # Xoá task gốc
    repo.delete_task("t-cascade")

    # Bản ghi con phải tự động bị xoá do ON DELETE CASCADE
    assert repo.get_task("t-cascade") is None
    assert len(repo.get_sources("t-cascade")) == 0
    assert repo.get_assignment_details("t-cascade") is None
    assert len(repo.list_conflicts("t-cascade")) == 0
    assert len(repo.list_pending_proposals("t-cascade")) == 0


def test_assignment_details_json_serialization(repo):
    repo.create_task({"id": "t-json", "title": "Task JSON", "status": "proposed"})
    details = {
        "raw_deadline_text": "hết ngày 15/11",
        "submission_format": [".zip", ".pdf"],
        "submission_platform": "LMS",
        "naming_convention": "MSSV_HoTen.zip",
        "grading_criteria": ["Rubric 1", "Rubric 2"],
        "assumptions": ["Không ghi giờ, giả định 23:59"]
    }
    repo.save_assignment_details("t-json", details)

    loaded = repo.get_assignment_details("t-json")
    assert loaded is not None
    assert loaded["submission_format"] == [".zip", ".pdf"]
    assert loaded["submission_platform"] == "LMS"
    assert loaded["grading_criteria"] == ["Rubric 1", "Rubric 2"]
    assert loaded["assumptions"] == ["Không ghi giờ, giả định 23:59"]


def test_conflict_resolution(repo):
    repo.create_task({"id": "t-conf", "title": "Task Conflict", "status": "proposed"})
    conf_id = repo.add_conflict({
        "task_id": "t-conf",
        "kind": "deadline",
        "value_a": "18/11",
        "value_b": "25/11",
        "suggestion": "b"
    })
    assert conf_id > 0

    conflicts = repo.list_conflicts("t-conf")
    assert len(conflicts) == 1
    assert conflicts[0]["resolution"] is None

    repo.resolve_conflict(conf_id, resolution="b")
    updated_conflicts = repo.list_conflicts("t-conf")
    assert updated_conflicts[0]["resolution"] == "b"
    assert updated_conflicts[0]["resolved_at"] is not None


def test_update_proposal_lifecycle(repo):
    repo.create_task({"id": "t-prop", "title": "Task Proposal", "status": "confirmed"})
    prop_id = repo.add_update_proposal({
        "task_id": "t-prop",
        "field": "deadline",
        "old_value": "18/11",
        "new_value": "25/11",
        "source": "email:e-update",
        "quote": "Dời hạn sang 25/11"
    })

    pending = repo.list_pending_proposals("t-prop")
    assert len(pending) == 1
    assert pending[0]["id"] == prop_id

    repo.set_update_proposal_status(prop_id, "accepted")
    assert len(repo.list_pending_proposals("t-prop")) == 0


def test_extraction_logs_and_cache(repo):
    log_id = repo.log_extraction({
        "source_type": "email",
        "source_id": "e-001",
        "content_hash": "hash_abc123",
        "prompt_version": "v1",
        "model_name": "fake",
        "prompt_tokens": 120,
        "completion_tokens": 80,
        "execution_time_ms": 150.5,
        "raw_response": '{"assignments": []}'
    })
    assert log_id > 0

    cached = repo.get_cached_extraction("e-001", "hash_abc123", "v1")
    assert cached is not None
    assert cached["prompt_tokens"] == 120
    assert cached["raw_response"] == '{"assignments": []}'

    # Kiểm tra trùng khoá UNIQUE (source_id, content_hash, prompt_version) sẽ ném lỗi
    with pytest.raises(sqlite3.IntegrityError):
        repo.log_extraction({
            "source_type": "email",
            "source_id": "e-001",
            "content_hash": "hash_abc123",
            "prompt_version": "v1",
            "model_name": "fake"
        })
