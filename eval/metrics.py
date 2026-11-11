"""Hệ thống chỉ số đánh giá thực nghiệm cho Module B.

Các chỉ số:
1. Field-level Precision, Recall, F1 cho các trường thông tin bài tập (tiêu đề, môn, hạn, nơi nộp, rubric).
2. Datetime Exact Match Accuracy (chính xác đến từng phút).
3. Conflict Detection Precision, Recall, F1 (phát hiện mâu thuẫn giữa email và tài liệu).
"""
from __future__ import annotations

import unicodedata
from datetime import datetime
from typing import Any, Iterable


def normalize_text(text: str | None) -> str:
    """Chuẩn hóa chuỗi văn bản: chữ thường, bỏ dấu tiếng Việt, gộp khoảng trắng."""
    if not text:
        return ""
    s = text.strip().lower()
    s = s.replace("đ", "d").replace("Đ", "d")
    nfkd = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(s.split())


def compute_field_metrics(
    gold_values: list[str | None],
    pred_values: list[str | None],
) -> dict[str, float]:
    """Tính Precision, Recall, F1 cho trường chuỗi đơn qua danh sách mẫu."""
    tp = 0
    fp = 0
    fn = 0

    for gold, pred in zip(gold_values, pred_values):
        norm_g = normalize_text(gold)
        norm_p = normalize_text(pred)

        if not norm_g and not norm_p:
            # Cả 2 đều None/rỗng: True Negative, bỏ qua không làm lệch Precision/Recall
            continue
        elif norm_g and norm_p:
            if norm_g == norm_p or norm_g in norm_p or norm_p in norm_g:
                tp += 1
            else:
                fp += 1
                fn += 1
        elif norm_g and not norm_p:
            fn += 1
        elif not norm_g and norm_p:
            fp += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def compute_list_field_metrics(
    gold_lists: list[list[str] | None],
    pred_lists: list[list[str] | None],
) -> dict[str, float]:
    """Tính Precision, Recall, F1 cho trường dạng danh sách (như grading_criteria, submission_format)."""
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for g_list, p_list in zip(gold_lists, pred_lists):
        set_g = {normalize_text(x) for x in (g_list or []) if normalize_text(x)}
        set_p = {normalize_text(x) for x in (p_list or []) if normalize_text(x)}

        tp = len(set_g.intersection(set_p))
        fp = len(set_p - set_g)
        fn = len(set_g - set_p)

        total_tp += tp
        total_fp += fp
        total_fn += fn

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": total_tp,
        "fp": total_fp,
        "fn": total_fn,
    }


def _parse_dt(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val))
    except Exception:
        return None


def datetime_exact_match(
    gold: datetime | str | None,
    pred: datetime | str | None,
) -> bool:
    """So khớp ngày giờ chính xác đến từng phút."""
    if gold is None and pred is None:
        return True
    if gold is None or pred is None:
        return False

    dt_g = _parse_dt(gold)
    dt_p = _parse_dt(pred)
    if dt_g is None or dt_p is None:
        return False

    val_g = dt_g.replace(tzinfo=None) if dt_g.tzinfo else dt_g
    val_p = dt_p.replace(tzinfo=None) if dt_p.tzinfo else dt_p

    return abs((val_g - val_p).total_seconds()) < 60


def compute_datetime_accuracy(
    gold_dts: list[Any],
    pred_dts: list[Any],
) -> float:
    """Tính tỉ lệ phần trăm khớp ngày giờ chính xác (Exact Match Accuracy)."""
    if not gold_dts:
        return 1.0
    matches = sum(1 for g, p in zip(gold_dts, pred_dts) if datetime_exact_match(g, p))
    return round(matches / len(gold_dts), 4)


def compute_conflict_metrics(
    gold_conflicts: list[bool],
    pred_conflicts: list[bool],
) -> dict[str, Any]:
    """Tính Precision, Recall, F1 cho bài toán phát hiện mâu thuẫn (nhị phân True/False)."""
    tp = sum(1 for g, p in zip(gold_conflicts, pred_conflicts) if g and p)
    fp = sum(1 for g, p in zip(gold_conflicts, pred_conflicts) if not g and p)
    fn = sum(1 for g, p in zip(gold_conflicts, pred_conflicts) if g and not p)
    tn = sum(1 for g, p in zip(gold_conflicts, pred_conflicts) if not g and not p)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "total": len(gold_conflicts),
    }
