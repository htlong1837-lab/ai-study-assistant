import io
from datetime import datetime, time

import pytest

from core.config import SAMPLE_DIR
from core.contracts import StudyBlock
from modules.scheduler.metrics import evaluate, missing_hours, validate
from modules.scheduler.model import ClassSession, ScheduleResult, ScheduleSettings
from modules.scheduler.slots import free_slots, to_blocks
from modules.scheduler.timetable import load_timetable_csv

from .conftest import MONDAY, task


# --- model ---

def test_settings_validation():
    with pytest.raises(ValueError):
        ScheduleSettings(days=0)
    with pytest.raises(ValueError):
        ScheduleSettings(slot_minutes=25)
    with pytest.raises(ValueError):
        ScheduleSettings(day_start=time(22), day_end=time(7))


def test_need_slots_rounds_up(settings):
    assert settings.need_slots(task("x", datetime(2026, 11, 20), 1.2)) == 3
    assert settings.need_slots(task("x", datetime(2026, 11, 20), 1.5)) == 3


def test_class_session_invalid():
    with pytest.raises(ValueError):
        ClassSession(7, time(7), time(9), "x")
    with pytest.raises(ValueError):
        ClassSession(0, time(9), time(7), "x")


# --- timetable ---

def test_load_sample_timetable():
    sessions, errors = load_timetable_csv(SAMPLE_DIR / "thoi_khoa_bieu.csv")
    assert errors == [] and len(sessions) == 6
    assert sessions[0].weekday == 0 and sessions[0].start == time(7, 0)


def test_timetable_reports_bad_rows_and_keeps_good():
    csv = "thu,bat_dau,ket_thuc,mon,phong\n2,7:00,9:30,AI,A1\n9,7:00,9:00,X,\nCN,8h,10h30,Y,\n3,10:00,9:00,Z,\n"
    sessions, errors = load_timetable_csv(io.BytesIO(csv.encode("utf-8")))
    assert [s.course for s in sessions] == ["AI", "Y"]
    assert sessions[1].weekday == 6 and sessions[1].end == time(10, 30)
    assert len(errors) == 2 and errors[0].startswith("Dòng 3")


def test_timetable_missing_columns():
    sessions, errors = load_timetable_csv(io.StringIO("ngay,gio\n1,2\n"))
    assert sessions == [] and "Thiếu cột" in errors[0]


# --- slots ---

def test_free_slots_skip_classes_and_window(sessions, settings):
    slots = free_slots(sessions, settings)
    monday = [s for s in slots if s.day == MONDAY]
    # 8h–20h = 24 ô; bỏ 8h–9h30 (3 ô) và 13h–15h30 (5 ô) → 16 ô
    assert len(monday) == 16
    assert all(not (s.start.hour == 13) for s in monday)
    assert monday[0].start == datetime(2026, 11, 9, 9, 30)
    assert [s.index for s in slots] == list(range(len(slots)))


def test_free_slots_not_before(sessions, settings):
    settings.not_before = datetime(2026, 11, 9, 18, 0)
    assert free_slots(sessions, settings)[0].start == datetime(2026, 11, 9, 18, 0)


def test_to_blocks_merges_contiguous(sessions, settings):
    s = free_slots(sessions, settings)
    blocks = to_blocks([("a", s[1]), ("a", s[0]), ("b", s[2]), ("a", s[4])])
    assert [(b.task_id, b.hours) for b in blocks] == [("a", 1.0), ("b", 0.5), ("a", 0.5)]


# --- metrics ---

def test_validate_detects_each_violation(sessions, settings, easy_tasks):
    blocks = [
        StudyBlock("a", datetime(2026, 11, 9, 13, 0), datetime(2026, 11, 9, 14, 0)),   # trùng lớp
        StudyBlock("a", datetime(2026, 11, 12, 9, 0), datetime(2026, 11, 12, 10, 0)),  # sau hạn
        StudyBlock("p", datetime(2026, 11, 10, 9, 0), datetime(2026, 11, 10, 10, 0)),  # chưa xác nhận
        StudyBlock("b", datetime(2026, 11, 13, 6, 0), datetime(2026, 11, 13, 9, 0)),   # ngoài khung giờ
        StudyBlock("c", datetime(2026, 11, 14, 9, 0), datetime(2026, 11, 14, 13, 0)),  # vượt 3 giờ/ngày
        StudyBlock("b", datetime(2026, 11, 14, 12, 0), datetime(2026, 11, 14, 12, 30)),  # trùng khối
    ]
    errors = " | ".join(validate(blocks, easy_tasks, sessions, settings))
    for needle in ["trùng giờ lên lớp", "sau hạn", "chưa được xác nhận",
                   "ngoài khung giờ", "vượt tối đa", "trùng giờ lúc"]:
        assert needle in errors


def test_missing_and_evaluate(sessions, settings, easy_tasks):
    blocks = [StudyBlock("a", datetime(2026, 11, 10, 9, 0), datetime(2026, 11, 10, 12, 0))]
    assert missing_hours(blocks, easy_tasks, settings) == {"b": 4.0, "c": 2.0}
    m = evaluate(ScheduleResult("X", blocks, {}, "GREEDY"), easy_tasks, sessions, settings)
    assert m["Kịp hạn"] == "1/3" and m["Giờ thiếu"] == 6.0
    assert m["Giờ thiếu (trọng số)"] == 4 * 2 + 2 * 1
    assert m["Xung đột"] == 0 and m["Đỉnh tải (giờ/ngày)"] == 3.0
