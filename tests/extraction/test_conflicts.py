from datetime import datetime
import pytest

from modules.extraction.conflicts import (
    compare_deadlines,
    compare_submission,
    detect_ambiguity,
    suggest_resolution,
)
from modules.extraction.datetime_normalizer import NormalizedDeadline
from modules.extraction.matcher import find_matching_task, token_similarity
from modules.extraction.schemas import Evidence, ExField, RawAssignment, RawDeadline


def test_compare_deadlines_7_days_mismatch():
    dt_a = datetime(2026, 11, 13, 23, 59)
    dt_b = datetime(2026, 11, 20, 23, 59)
    res = compare_deadlines(dt_a, dt_b)
    assert res is not None
    assert res["kind"] == "deadline"
    assert res["diff_hours"] == 168.0  # 7 ngày * 24h


def test_compare_deadlines_same_day_time_defaulted_no_conflict():
    # Một bên ghi 17h00 (time_defaulted=False), một bên hệ thống tự gán 23h59 (time_defaulted=True)
    nd_a = NormalizedDeadline(
        value=datetime(2026, 11, 20, 17, 0),
        anchor=datetime(2026, 11, 9, 8, 0),
        time_defaulted=False,
    )
    nd_b = NormalizedDeadline(
        value=datetime(2026, 11, 20, 23, 59),
        anchor=datetime(2026, 11, 9, 8, 0),
        time_defaulted=True,
    )
    res = compare_deadlines(nd_a, nd_b)
    # Cùng ngày và có time_defaulted -> Không báo lỗi sai
    assert res is None


def test_compare_deadlines_same_day_both_explicit_conflict():
    nd_a = NormalizedDeadline(
        value=datetime(2026, 11, 20, 17, 0),
        anchor=datetime(2026, 11, 9, 8, 0),
        time_defaulted=False,
    )
    nd_b = NormalizedDeadline(
        value=datetime(2026, 11, 20, 23, 59),
        anchor=datetime(2026, 11, 9, 8, 0),
        time_defaulted=False,
    )
    res = compare_deadlines(nd_a, nd_b)
    assert res is not None
    assert res["kind"] == "deadline"
    assert res["diff_hours"] == 6.98 or round(res["diff_hours"], 1) == 7.0


def test_compare_submission_mismatches():
    conflicts = compare_submission(
        platform_a="LMS trường",
        platform_b="GitHub Classroom",
        format_a=[".zip", ".pdf"],
        format_b=[".git"],
    )
    kinds = [c["kind"] for c in conflicts]
    assert "submission_platform" in kinds
    assert "submission_format" in kinds


def test_detect_ambiguity_flags():
    raw_a = RawAssignment(
        title=ExField(value="Bài tập 1", evidence=Evidence(quote="Bài tập 1", location="p1")),
        course=ExField(value="AI", evidence=Evidence(quote="AI", location="p1")),
        deadlines=[
            RawDeadline(raw_text="tuần sau", evidence=Evidence(quote="tuần sau", location="p1"))
        ],
        submission_platform=ExField(value=None, evidence=None),
        grading_criteria=ExField(value=None, evidence=None),
    )
    norm_dl = [
        NormalizedDeadline(
            value=datetime(2026, 11, 15, 23, 59),
            anchor=datetime(2026, 11, 9, 8, 0),
            flags=["AMBIGUOUS"],
        )
    ]
    warnings = detect_ambiguity(raw_a, norm_dl)
    assert "ambiguous_deadline" in warnings
    assert "missing_platform" in warnings
    assert "missing_rubric" in warnings


def test_suggest_resolution_favors_extension():
    sugg = suggest_resolution(is_extension_a=False, is_extension_b=True)
    assert sugg == "b"


class FakeRepo:
    def list_tasks(self):
        return [
            {
                "id": "t-001",
                "title": "Báo cáo SP1 môn Trí tuệ nhân tạo",
                "course": "Trí tuệ nhân tạo",
                "status": "confirmed",
                "deadline": "2026-11-13T23:59:00",
            },
            {
                "id": "t-002",
                "title": "Bài tập chương 2 CSDL",
                "course": "Cơ sở dữ liệu",
                "status": "confirmed",
                "deadline": "2026-11-15T23:59:00",
            },
        ]


def test_matcher_finds_task_by_title_and_refers_to():
    repo = FakeRepo()

    # 1. Khớp qua refers_to
    raw1 = RawAssignment(
        title=ExField(value="Thông báo dời hạn nộp", evidence=None),
        refers_to="Báo cáo SP1",
    )
    matched1 = find_matching_task(raw1, repo)
    assert matched1 is not None
    assert matched1["id"] == "t-001"

    # 2. Khớp qua độ tương đồng title + course
    raw2 = RawAssignment(
        title=ExField(value="Báo cáo SP1 AI", evidence=None),
        course=ExField(value="Trí tuệ nhân tạo", evidence=None),
    )
    matched2 = find_matching_task(raw2, repo)
    assert matched2 is not None
    assert matched2["id"] == "t-001"

    # 3. Không khớp khi dưới ngưỡng
    raw3 = RawAssignment(
        title=ExField(value="Thi Olympic Tin học", evidence=None),
        course=ExField(value="Toán rời rạc", evidence=None),
    )
    matched3 = find_matching_task(raw3, repo)
    assert matched3 is None
