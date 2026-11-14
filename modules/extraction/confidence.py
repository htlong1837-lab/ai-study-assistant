"""Động cơ tính toán độ tin cậy (confidence score) bằng code tất định.

Nguyên tắc cốt lõi:
- Tuyệt đối không dùng số tự chấm của LLM (LLM hay tự chấm 1.0 hoặc bịa điểm).
- Tính toán dựa trên tính đầy đủ của các trường thông tin cốt lõi, sự hợp lệ của trích dẫn bằng chứng,
  các giả định chuẩn hóa và các cờ cảnh báo (AMBIGUOUS, UNRESOLVED, OUTDATED_DEADLINE).
"""
from __future__ import annotations

from modules.extraction.datetime_normalizer import NormalizedDeadline
from modules.extraction.schemas import RawAssignment

# Trọng số phạt điểm (Constants có thể tinh chỉnh)
PENALTY_MISSING_TITLE = 0.30
PENALTY_MISSING_COURSE = 0.15
PENALTY_NO_DEADLINE = 0.35
PENALTY_UNRESOLVED_DEADLINE = 0.30
PENALTY_EVIDENCE_NOT_FOUND = 0.15
PENALTY_FLAG_AMBIGUOUS = 0.20
PENALTY_FLAG_OUTDATED = 0.15
PENALTY_TIME_DEFAULTED = 0.05
PENALTY_PER_ASSUMPTION = 0.03


def compute_confidence(
    raw: RawAssignment,
    normalized_deadlines: list[NormalizedDeadline],
    warnings: list[str],
) -> float:
    """Tính toán điểm độ tin cậy trong khoảng [0.0, 1.0] cho một đề xuất bài tập."""
    score = 1.0

    # 1. Kiểm tra Tiêu đề
    if not raw.title.value or not str(raw.title.value).strip():
        score -= PENALTY_MISSING_TITLE

    # 2. Kiểm tra Môn học
    if not raw.course.value or not str(raw.course.value).strip():
        score -= PENALTY_MISSING_COURSE

    # 3. Kiểm tra Hạn nộp
    if not normalized_deadlines:
        score -= PENALTY_NO_DEADLINE
    else:
        for nd in normalized_deadlines:
            if nd.value is None:
                score -= PENALTY_UNRESOLVED_DEADLINE
            if nd.time_defaulted:
                score -= PENALTY_TIME_DEFAULTED
            if "AMBIGUOUS" in nd.flags:
                score -= PENALTY_FLAG_AMBIGUOUS
            if "OUTDATED_DEADLINE" in nd.flags:
                score -= PENALTY_FLAG_OUTDATED
            # Phạt nhẹ cho mỗi giả định chuẩn hoá
            score -= len(nd.assumptions) * PENALTY_PER_ASSUMPTION

    # 4. Kiểm tra Cảnh báo về Bằng chứng giả / không tìm thấy
    for w in warnings:
        if "evidence_not_found" in w:
            score -= PENALTY_EVIDENCE_NOT_FOUND

    return max(0.0, min(1.0, round(score, 2)))
