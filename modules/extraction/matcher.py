"""Bộ so khớp bài tập giữa các nguồn khác nhau (Module B).

Xác định xem một trích xuất mới (ví dụ từ email) có cùng nói về một bài tập
đã tồn tại trong DB (ví dụ từ đề bài PDF trước đó) hay không.
"""
from __future__ import annotations

import re
from typing import Any

from db.repository import Repository
from modules.extraction.schemas import RawAssignment


def _tokenize(text: str) -> set[str]:
    """Tách từ đơn giản cho tiếng Việt, chuẩn hóa chữ thường."""
    if not text:
        return set()
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return {w for w in cleaned.split() if len(w) > 1}


def token_similarity(str1: str, str2: str) -> float:
    """Tính độ tương đồng giữa hai chuỗi dựa trên tập từ (kết hợp Jaccard và Containment)."""
    t1 = _tokenize(str1)
    t2 = _tokenize(str2)
    if not t1 or not t2:
        return 0.0
    intersection = t1.intersection(t2)
    union = t1.union(t2)
    jaccard = len(intersection) / len(union)
    containment = len(intersection) / min(len(t1), len(t2))
    return 0.7 * containment + 0.3 * jaccard


def find_matching_task(
    raw_assignment: RawAssignment,
    repo: Repository,
    similarity_threshold: float = 0.55,
) -> dict[str, Any] | None:
    """Tìm bài tập đã tồn tại trong CSDL khớp với bài tập đang trích xuất.

    Thứ tự ưu tiên:
    1. So khớp theo trường `refers_to` (nếu có).
    2. So khớp theo độ tương đồng tiêu đề bài tập và môn học.
    3. An toàn mặc định: Dưới ngưỡng thì trả về None.
    """
    all_tasks = repo.list_tasks()
    if not all_tasks:
        return None

    refers_to = raw_assignment.refers_to.strip() if raw_assignment.refers_to else None
    title = raw_assignment.title.value.strip() if raw_assignment.title and raw_assignment.title.value else ""
    course = raw_assignment.course.value.strip() if raw_assignment.course and raw_assignment.course.value else ""

    # 1. Khớp qua refers_to
    if refers_to:
        refers_clean = refers_to.lower()
        for t in all_tasks:
            t_title = (t.get("title") or "").lower()
            if refers_clean in t_title or t_title in refers_clean:
                return t
            if token_similarity(refers_to, t.get("title") or "") >= 0.5:
                return t

    if not title:
        return None

    # 2. Khớp qua Title + Course
    best_match: dict[str, Any] | None = None
    best_score: float = 0.0

    for t in all_tasks:
        t_title = t.get("title") or ""
        t_course = t.get("course") or ""

        title_sim = token_similarity(title, t_title)
        
        # Nếu môn học được cung cấp ở cả hai phía, kiểm tra trùng khớp môn
        course_penalty = 1.0
        if course and t_course:
            course_sim = token_similarity(course, t_course)
            if course_sim < 0.3:
                course_penalty = 0.5
            else:
                course_penalty = 1.1

        combined_score = title_sim * course_penalty
        if combined_score > best_score:
            best_score = combined_score
            best_match = t

    if best_score >= similarity_threshold:
        return best_match

    return None
