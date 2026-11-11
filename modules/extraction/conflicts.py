"""Phát hiện mâu thuẫn tất định và phát hiện sự mơ hồ (Module B).

So sánh đối chiếu giữa các nguồn (ví dụ email và tài liệu PDF) về:
- Hạn nộp (xử lý ca time_defaulted: cùng ngày nhưng khác giờ mặc định không báo mâu thuẫn).
- Kênh và định dạng nộp bài.
- Phát hiện các điểm mơ hồ (thiếu rubric, thiếu kênh nộp, hạn nộp chung chung).
- Gợi ý phương án giải quyết (ưu tiên email đính chính / gia hạn).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from modules.extraction.datetime_normalizer import NormalizedDeadline
from modules.extraction.schemas import RawAssignment


def _parse_dt(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val))
    except Exception:
        return None


def compare_deadlines(
    deadline_a: NormalizedDeadline | datetime | str | None,
    deadline_b: NormalizedDeadline | datetime | str | None,
    time_defaulted_a: bool = False,
    time_defaulted_b: bool = False,
) -> dict[str, Any] | None:
    """So sánh hai hạn nộp từ hai nguồn khác nhau.

    Quy tắc:
    - Nếu một trong hai nguồn do hệ thống tự gán giờ mặc định 23:59 (`time_defaulted = True`),
      chỉ so sánh ở mức ngày (`date()`). Nếu cùng ngày thì coi như không mâu thuẫn.
    - Nếu cả hai đều ghi rõ giờ hoặc lệch ngày: báo mâu thuẫn.
    """
    if deadline_a is None or deadline_b is None:
        return None

    dt_a = deadline_a.value if isinstance(deadline_a, NormalizedDeadline) else _parse_dt(deadline_a)
    dt_b = deadline_b.value if isinstance(deadline_b, NormalizedDeadline) else _parse_dt(deadline_b)

    if dt_a is None or dt_b is None:
        return None

    def_a = deadline_a.time_defaulted if isinstance(deadline_a, NormalizedDeadline) else time_defaulted_a
    def_b = deadline_b.time_defaulted if isinstance(deadline_b, NormalizedDeadline) else time_defaulted_b

    # Chuẩn hoá naive vs aware (nếu có)
    val_a = dt_a.replace(tzinfo=None) if dt_a.tzinfo else dt_a
    val_b = dt_b.replace(tzinfo=None) if dt_b.tzinfo else dt_b

    if def_a or def_b:
        # Ít nhất một bên tự gán giờ -> chỉ so sánh ngày
        if val_a.date() == val_b.date():
            return None
    else:
        # Cả hai bên đều có giờ rõ ràng -> so sánh phút
        if abs((val_a - val_b).total_seconds()) < 60:
            return None

    diff_hours = abs((val_a - val_b).total_seconds()) / 3600.0
    return {
        "kind": "deadline",
        "value_a": val_a.isoformat(),
        "value_b": val_b.isoformat(),
        "diff_hours": round(diff_hours, 2),
    }


def compare_submission(
    platform_a: str | None,
    platform_b: str | None,
    format_a: list[str] | str | None = None,
    format_b: list[str] | str | None = None,
) -> list[dict[str, Any]]:
    """So sánh kênh nộp và định dạng nộp bài giữa hai nguồn."""
    conflicts: list[dict[str, Any]] = []

    def _norm(s: str | None) -> str:
        return (s or "").strip().lower()

    if platform_a and platform_b and _norm(platform_a) != _norm(platform_b):
        conflicts.append({
            "kind": "submission_platform",
            "value_a": platform_a.strip(),
            "value_b": platform_b.strip(),
        })

    def _to_set(val: Any) -> set[str]:
        if not val:
            return set()
        if isinstance(val, list):
            return {_norm(x) for x in val if x}
        return {_norm(val)}

    set_a = _to_set(format_a)
    set_b = _to_set(format_b)
    if set_a and set_b and set_a != set_b:
        conflicts.append({
            "kind": "submission_format",
            "value_a": ", ".join(sorted(set_a)),
            "value_b": ", ".join(sorted(set_b)),
        })

    return conflicts


def detect_ambiguity(
    raw_assignment: RawAssignment,
    norm_deadlines: list[NormalizedDeadline] | None = None,
) -> list[str]:
    """Phát hiện các điểm mơ hồ trong trích xuất."""
    warnings: list[str] = []

    if norm_deadlines:
        for nd in norm_deadlines:
            flags = nd.flags or []
            if "AMBIGUOUS" in flags:
                warnings.append("ambiguous_deadline")
            elif "UNRESOLVED" in flags:
                warnings.append("unresolved_deadline")
    elif not raw_assignment.deadlines:
        warnings.append("missing_deadline")

    if not raw_assignment.submission_platform or not raw_assignment.submission_platform.value:
        warnings.append("missing_platform")

    if not raw_assignment.grading_criteria or not raw_assignment.grading_criteria.value:
        warnings.append("missing_rubric")

    return warnings


def suggest_resolution(
    is_extension_a: bool = False,
    is_extension_b: bool = False,
    date_a: datetime | None = None,
    date_b: datetime | None = None,
) -> str:
    """Gợi ý phương án giải quyết (chọn 'a' hoặc 'b').

    Ưu tiên:
    1. Bên nào là thông báo dời hạn / gia hạn thì ưu tiên bên đó.
    2. Nếu không có cờ gia hạn, ưu tiên mốc thời gian muộn hơn (hoặc mới cập nhật hơn).
    """
    if is_extension_b and not is_extension_a:
        return "b"
    if is_extension_a and not is_extension_b:
        return "a"
    if date_a and date_b:
        return "b" if date_b > date_a else "a"
    return "b"  # Mặc định nghiêng về nguồn đến sau (B)
