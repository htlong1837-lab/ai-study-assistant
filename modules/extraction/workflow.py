"""Quy trình nghiệp vụ và máy trạng thái quản lý vòng đời bài tập (Module B).

Tuân thủ nguyên tắc:
1. AI chỉ đề xuất, người dùng quyết định: Task mới luôn là 'proposed', chỉ 'confirm()' mới chuyển sang 'confirmed'.
2. Cổng chặn tại cửa vào: Kiểm tra can_forward trước khi xử lý email.
3. Không bao giờ xác nhận task khi thiếu deadline hoặc còn mâu thuẫn chưa giải quyết.
4. Cầu nối chuyển giao sang core.contracts.Task cho Module C lập lịch.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from core.contracts import ClassifiedEmail, ParsedDocument, Priority, Task, TaskStatus, can_forward
from core.llm_client import LLMClient
from db.repository import Repository
from modules.extraction.conflicts import compare_deadlines, compare_submission, suggest_resolution
from modules.extraction.extractor import extract_from_document, extract_from_email
from modules.extraction.gate import ensure_safe
from modules.extraction.matcher import find_matching_task


def _ensure_dt(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val))
    except Exception:
        return None


def process_email(
    email: ClassifiedEmail,
    llm: LLMClient,
    repo: Repository,
    allow_suspicious: bool = False,
) -> list[str]:
    """Xử lý email an toàn: Trích xuất, chuẩn hóa thời gian, so khớp bài tập cũ.

    Lưu vào DB ở trạng thái 'proposed' (hoặc tạo proposal cập nhật nếu là email dời hạn).
    Trả về danh sách task_id được tạo mới hoặc liên quan.
    Ném ngoại lệ UnsafeSourceError nếu email không an toàn.
    """
    ensure_safe(email, allow_suspicious=allow_suspicious)

    outcome = extract_from_email(email, llm, repo=repo, allow_suspicious=allow_suspicious)
    if outcome.is_empty or not outcome.items:
        return []

    created_or_updated_task_ids: list[str] = []

    for item in outcome.items:
        raw_a = item.assignment
        norm_deadline = item.normalized_deadlines[0] if item.normalized_deadlines else None
        deadline_dt = norm_deadline.value if norm_deadline else None
        deadline_iso = deadline_dt.isoformat() if deadline_dt else None

        # Kiểm tra xem có bài tập nào đã tồn tại trong DB khớp với bài này không
        matching_task = find_matching_task(raw_a, repo)

        if matching_task:
            task_id = matching_task["id"]
            # Nếu là email dời hạn / đính chính hoặc task đã confirmed nhưng có deadline mới khác
            old_deadline_str = matching_task.get("deadline")
            old_deadline_dt = _ensure_dt(old_deadline_str)

            if raw_a.is_extension_notice or (deadline_dt and old_deadline_dt and deadline_dt != old_deadline_dt):
                # Tạo đề xuất cập nhật (task_update_proposals)
                quote = ""
                if raw_a.deadlines and raw_a.deadlines[0].evidence:
                    quote = raw_a.deadlines[0].evidence.quote

                repo.add_update_proposal({
                    "task_id": task_id,
                    "field": "deadline",
                    "old_value": old_deadline_str,
                    "new_value": deadline_iso,
                    "source": f"email:{email.id}",
                    "quote": quote,
                    "status": "pending",
                })
                # Đồng thời thêm vào task_sources
                repo.add_sources(task_id, item.sources)
                created_or_updated_task_ids.append(task_id)
                continue

        # Tạo task mới ở trạng thái PROPOSED
        task_id = f"t-{uuid.uuid4().hex[:8]}"
        title_val = (raw_a.title.value or "Bài tập mới").strip()
        course_val = (raw_a.course.value or "Chung").strip() if raw_a.course else "Chung"
        est_hours = raw_a.estimated_hours if raw_a.estimated_hours and raw_a.estimated_hours > 0 else 2.0
        priority_val = raw_a.priority_suggestion.value if raw_a.priority_suggestion else "medium"

        repo.create_task({
            "id": task_id,
            "title": title_val,
            "course": course_val,
            "deadline": deadline_iso,
            "estimated_hours": est_hours,
            "priority": priority_val,
            "confidence": item.confidence,
            "status": "proposed",
        })

        if item.sources:
            repo.add_sources(task_id, item.sources)

        # Lưu chi tiết yêu cầu bài tập (bảng assignment_details)
        sub_platform = raw_a.submission_platform.value if raw_a.submission_platform else None
        sub_format = raw_a.submission_format.value if raw_a.submission_format else None
        naming = raw_a.naming_convention.value if raw_a.naming_convention else None
        rubric = raw_a.grading_criteria.value if raw_a.grading_criteria else None
        raw_deadline_text = raw_a.deadlines[0].raw_text if raw_a.deadlines else None

        repo.save_assignment_details(task_id, {
            "raw_deadline_text": raw_deadline_text,
            "submission_platform": sub_platform,
            "submission_format": sub_format,
            "naming_convention": naming,
            "grading_criteria": rubric,
            "assumptions": norm_deadline.assumptions if norm_deadline else [],
        })

        created_or_updated_task_ids.append(task_id)

    return created_or_updated_task_ids


def process_document(
    doc: ParsedDocument,
    llm: LLMClient,
    repo: Repository,
    linked_email: ClassifiedEmail | None = None,
    pages: list[int] | None = None,
) -> list[str]:
    """Xử lý tài liệu đề bài: Trích xuất thông tin, đối chiếu mâu thuẫn với email liên kết (nếu có),
    lưu vào DB ở trạng thái 'proposed'."""
    outcome = extract_from_document(doc, llm, repo=repo, pages=pages)
    if outcome.is_empty or not outcome.items:
        return []

    created_task_ids: list[str] = []

    for item in outcome.items:
        raw_a = item.assignment
        norm_deadline = item.normalized_deadlines[0] if item.normalized_deadlines else None
        deadline_dt = norm_deadline.value if norm_deadline else None
        deadline_iso = deadline_dt.isoformat() if deadline_dt else None

        task_id = f"t-{uuid.uuid4().hex[:8]}"
        title_val = (raw_a.title.value or doc.filename).strip()
        course_val = (raw_a.course.value or "Chung").strip() if raw_a.course else "Chung"
        est_hours = raw_a.estimated_hours if raw_a.estimated_hours and raw_a.estimated_hours > 0 else 3.0
        priority_val = raw_a.priority_suggestion.value if raw_a.priority_suggestion else "medium"

        repo.create_task({
            "id": task_id,
            "title": title_val,
            "course": course_val,
            "deadline": deadline_iso,
            "estimated_hours": est_hours,
            "priority": priority_val,
            "confidence": item.confidence,
            "status": "proposed",
        })

        if item.sources:
            repo.add_sources(task_id, item.sources)

        # Lưu assignment_details
        sub_platform = raw_a.submission_platform.value if raw_a.submission_platform else None
        sub_format = raw_a.submission_format.value if raw_a.submission_format else None
        naming = raw_a.naming_convention.value if raw_a.naming_convention else None
        rubric = raw_a.grading_criteria.value if raw_a.grading_criteria else None
        raw_deadline_text = raw_a.deadlines[0].raw_text if raw_a.deadlines else None

        repo.save_assignment_details(task_id, {
            "raw_deadline_text": raw_deadline_text,
            "submission_platform": sub_platform,
            "submission_format": sub_format,
            "naming_convention": naming,
            "grading_criteria": rubric,
            "assumptions": norm_deadline.assumptions if norm_deadline else [],
        })

        # Đối chiếu mâu thuẫn với email liên kết nếu có
        if linked_email:
            linked_sources = repo.get_sources(task_id)
            # Thêm nguồn email vào task
            repo.add_sources(task_id, [{
                "source": f"email:{linked_email.id}",
                "field": "linked_email",
                "quote": linked_email.subject,
                "kind": "email",
            }])

        created_task_ids.append(task_id)

    return created_task_ids


def confirm(
    task_id: str,
    repo: Repository,
    overrides: dict[str, Any] | None = None,
) -> Task:
    """Chuyển trạng thái task từ 'proposed' sang 'confirmed'.

    Cho phép ghi đè deadline, estimated_hours, priority qua overrides.
    Bắt buộc task phải có deadline hợp lệ mới được xác nhận.
    Chặn nếu còn mâu thuẫn chưa được giải quyết.
    Trả về đối tượng Task hợp lệ theo core.contracts.Task.
    """
    task_row = repo.get_task(task_id)
    if not task_row:
        raise ValueError(f"Task '{task_id}' không tồn tại trong hệ thống")

    if task_row["status"] == "cancelled":
        raise ValueError("Task đã bị huỷ trước đó, không thể chuyển trực tiếp sang 'confirmed'")

    if task_row["status"] != "proposed":
        raise ValueError(f"Chỉ xác nhận được task ở trạng thái 'proposed', trạng thái hiện tại: '{task_row['status']}'")

    # Kiểm tra mâu thuẫn chưa giải quyết
    conflicts = repo.list_conflicts(task_id)
    unresolved = [c for c in conflicts if not c.get("resolution")]
    if unresolved:
        raise ValueError(f"Task còn {len(unresolved)} mâu thuẫn chưa giải quyết, không thể xác nhận vào lịch")

    # Áp dụng overrides nếu có
    update_data: dict[str, Any] = {}
    if overrides:
        if "deadline" in overrides:
            dl_override = overrides["deadline"]
            if isinstance(dl_override, datetime):
                update_data["deadline"] = dl_override.isoformat()
            elif isinstance(dl_override, str):
                update_data["deadline"] = dl_override
        if "estimated_hours" in overrides:
            update_data["estimated_hours"] = float(overrides["estimated_hours"])
        if "priority" in overrides:
            update_data["priority"] = str(overrides["priority"])
        if "title" in overrides:
            update_data["title"] = str(overrides["title"])
        if "course" in overrides:
            update_data["course"] = str(overrides["course"])

        if update_data:
            repo.update_task_fields(task_id, **update_data)
            task_row = repo.get_task(task_id)
            assert task_row is not None

    # Bắt buộc phải có hạn nộp hợp lệ
    deadline_val = task_row.get("deadline")
    if not deadline_val or not str(deadline_val).strip():
        raise ValueError("Task chưa có hạn nộp (deadline), không thể xác nhận vào lịch. Vui lòng nhập hạn nộp bổ sung.")

    now_iso = datetime.now(timezone.utc).isoformat()
    repo.set_task_status(task_id, "confirmed", confirmed_at=now_iso)

    updated_row = repo.get_task(task_id)
    assert updated_row is not None
    return to_contract_task(updated_row, repo=repo)


def cancel(task_id: str, repo: Repository) -> None:
    """Người dùng từ chối / hủy đề xuất (chuyển sang 'cancelled')."""
    task_row = repo.get_task(task_id)
    if not task_row:
        raise ValueError(f"Task '{task_id}' không tồn tại trong hệ thống")

    if task_row["status"] == "cancelled":
        raise ValueError("Task đã ở trạng thái 'cancelled'")

    repo.set_task_status(task_id, "cancelled")


def resolve_conflict(
    conflict_id: int,
    choice: Literal["a", "b", "manual"],
    manual_value: str | None = None,
    repo: Repository = ...,
) -> None:
    """Người dùng lựa chọn phương án giải quyết mâu thuẫn giữa 2 nguồn."""
    all_conflicts = repo.list_conflicts()
    target_conflict = next((c for c in all_conflicts if c["id"] == conflict_id), None)
    if not target_conflict:
        raise ValueError(f"Conflict với id {conflict_id} không tồn tại")

    resolution_str = ""
    chosen_value: str | None = None

    if choice == "a":
        chosen_value = target_conflict.get("value_a")
        resolution_str = f"use_a:{chosen_value}"
    elif choice == "b":
        chosen_value = target_conflict.get("value_b")
        resolution_str = f"use_b:{chosen_value}"
    elif choice == "manual":
        chosen_value = manual_value
        resolution_str = f"manual:{manual_value}"
    else:
        raise ValueError(f"Lựa chọn choice '{choice}' không hợp lệ (cho phép: 'a', 'b', 'manual')")

    repo.resolve_conflict(conflict_id, resolution_str)

    # Nếu xung đột liên quan đến hạn nộp, cập nhật hạn nộp cho task tương ứng
    task_id = target_conflict["task_id"]
    if target_conflict.get("kind") == "deadline" and chosen_value:
        repo.update_task_fields(task_id, deadline=chosen_value)


def accept_update_proposal(proposal_id: int, repo: Repository) -> Task:
    """Người dùng chấp thuận đề xuất cập nhật bài tập đã có. Cập nhật thông tin mới vào task."""
    proposals = repo.list_pending_proposals()
    target_proposal = next((p for p in proposals if p["id"] == proposal_id), None)
    if not target_proposal:
        raise ValueError(f"Proposal với id {proposal_id} không tồn tại hoặc không ở trạng thái pending")

    task_id = target_proposal["task_id"]
    field_to_update = target_proposal["field"]
    new_value = target_proposal["new_value"]

    if field_to_update == "deadline":
        repo.update_task_fields(task_id, deadline=new_value)
    elif field_to_update in ("title", "course", "priority", "estimated_hours"):
        repo.update_task_fields(task_id, **{field_to_update: new_value})

    repo.set_update_proposal_status(proposal_id, "accepted")

    updated_row = repo.get_task(task_id)
    assert updated_row is not None
    # Nếu task đã confirmed, trả về contract Task
    if updated_row["status"] == "confirmed":
        return to_contract_task(updated_row, repo=repo)

    # Nếu task đang proposed, trả về Task đã chuyển confirmed hoặc giữ contract Task
    return to_contract_task(updated_row, repo=repo, force_schedulable=True)


def reject_update_proposal(proposal_id: int, repo: Repository) -> None:
    """Người dùng từ chối đề xuất dời hạn (giữ nguyên thông tin cũ của task)."""
    proposals = repo.list_pending_proposals()
    target_proposal = next((p for p in proposals if p["id"] == proposal_id), None)
    if not target_proposal:
        raise ValueError(f"Proposal với id {proposal_id} không tồn tại hoặc không ở trạng thái pending")

    repo.set_update_proposal_status(proposal_id, "rejected")


def to_contract_task(
    task_row: dict[str, Any],
    repo: Repository | None = None,
    force_schedulable: bool = False,
) -> Task:
    """Chuyển đổi bản ghi CSDL sang dataclass core.contracts.Task.

    Chỉ cho phép chuyển đổi nếu status == 'confirmed' (hoặc force_schedulable=True)
    và deadline is not None.
    """
    status_str = task_row.get("status")
    if not force_schedulable and status_str != "confirmed":
        raise ValueError(f"Chỉ cho phép chuyển đổi task 'confirmed' sang contracts.Task, hiện tại: '{status_str}'")

    raw_deadline = task_row.get("deadline")
    if not raw_deadline:
        raise ValueError("Task thiếu deadline, không thể chuyển đổi sang contracts.Task")

    deadline_dt = _ensure_dt(raw_deadline)
    if not deadline_dt:
        raise ValueError(f"Không thể phân tích cú pháp deadline: {raw_deadline}")

    # Xoá timezone info nếu core contracts yêu cầu datetime nhất quán
    if deadline_dt.tzinfo is not None:
        deadline_dt = deadline_dt.replace(tzinfo=None)

    # Tìm nguồn trích xuất
    source = f"task:{task_row['id']}"
    if repo:
        sources = repo.get_sources(task_row["id"])
        if sources:
            source = sources[0]["source"]

    status_enum = TaskStatus.CONFIRMED if (status_str == "confirmed" or force_schedulable) else TaskStatus(status_str)
    priority_enum = Priority(task_row.get("priority", "medium"))
    est_hours = float(task_row.get("estimated_hours") or 2.0)
    if est_hours <= 0:
        est_hours = 1.0

    return Task(
        id=task_row["id"],
        title=task_row["title"],
        course=task_row.get("course") or "Chung",
        deadline=deadline_dt,
        estimated_hours=est_hours,
        source=source,
        confidence=float(task_row.get("confidence", 1.0)),
        priority=priority_enum,
        status=status_enum,
    )
