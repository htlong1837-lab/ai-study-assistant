from datetime import datetime
import pytest

from eval.metrics import (
    compute_conflict_metrics,
    compute_datetime_accuracy,
    compute_field_metrics,
    compute_list_field_metrics,
    datetime_exact_match,
    normalize_text,
)


def test_normalize_text():
    assert normalize_text("  ĐỀ BÀI TẬP LỚN  ") == "de bai tap lon"
    assert normalize_text(None) == ""


def test_compute_field_metrics():
    gold = ["Báo cáo SP1", "Bài tập 2", "Đồ án tốt nghiệp", None]
    pred = ["Báo cáo SP1", "Bài tập 3", "Đồ án tốt nghiệp", None]

    # Mẫu 1: đúng (TP)
    # Mẫu 2: lệch (FP + FN)
    # Mẫu 3: đúng (TP)
    # Mẫu 4: cả 2 rỗng (TN - bỏ qua)
    # TP = 2, FP = 1, FN = 1
    # Precision = 2 / 3 = 0.6667
    # Recall = 2 / 3 = 0.6667
    # F1 = 0.6667
    metrics = compute_field_metrics(gold, pred)
    assert metrics["tp"] == 2
    assert metrics["fp"] == 1
    assert metrics["fn"] == 1
    assert metrics["f1"] == 0.6667


def test_compute_list_field_metrics():
    gold = [["LMS", "Email"], [".zip", ".pdf"]]
    pred = [["lms"], [".zip", ".docx"]]

    # List 1: TP=1 (lms), FP=0, FN=1 (email)
    # List 2: TP=1 (.zip), FP=1 (.docx), FN=1 (.pdf)
    # Total TP=2, FP=1, FN=2
    # Precision = 2 / 3 = 0.6667
    # Recall = 2 / 4 = 0.5
    # F1 = 2 * (2/3) * (1/2) / (2/3 + 1/2) = (2/3) / (7/6) = 4/7 = 0.5714
    metrics = compute_list_field_metrics(gold, pred)
    assert metrics["tp"] == 2
    assert metrics["fp"] == 1
    assert metrics["fn"] == 2
    assert metrics["f1"] == 0.5714


def test_datetime_exact_match():
    dt1 = datetime(2026, 11, 20, 23, 59)
    dt2 = "2026-11-20T23:59:00"
    dt3 = datetime(2026, 11, 20, 23, 58)

    assert datetime_exact_match(dt1, dt2) is True
    assert datetime_exact_match(dt1, dt3) is False
    assert datetime_exact_match(None, None) is True
    assert datetime_exact_match(dt1, None) is False


def test_compute_datetime_accuracy():
    gold = ["2026-11-20T23:59:00", "2026-11-25T17:00:00", None]
    pred = ["2026-11-20T23:59:00", "2026-11-25T18:00:00", None]
    # 2/3 đúng
    acc = compute_datetime_accuracy(gold, pred)
    assert acc == 0.6667


def test_compute_conflict_metrics():
    gold = [True, True, False, False]
    pred = [True, False, True, False]
    # TP = 1 (mẫu 0)
    # FN = 1 (mẫu 1)
    # FP = 1 (mẫu 2)
    # TN = 1 (mẫu 3)
    res = compute_conflict_metrics(gold, pred)
    assert res["tp"] == 1
    assert res["fn"] == 1
    assert res["fp"] == 1
    assert res["tn"] == 1
    assert res["f1"] == 0.5
