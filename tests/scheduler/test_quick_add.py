from datetime import datetime

from core.contracts import Priority
from modules.scheduler.quick_add import DEFAULT_HOURS, parse

NOW = datetime(2026, 11, 25, 10, 0)  # thứ Tư
COURSES = ["Trí tuệ nhân tạo", "Cơ sở dữ liệu (thực hành)", "Cơ sở dữ liệu", "Mạng máy tính"]


def test_full_sentence():
    q = parse("Báo cáo CSDL 23h59 thứ Sáu tuần sau, 3 giờ, gấp", NOW, COURSES)
    assert q.title == "Báo cáo CSDL"
    assert q.deadline == datetime(2026, 12, 4, 23, 59)
    assert q.hours == 3.0
    assert q.priority is Priority.HIGH
    assert q.course == "Cơ sở dữ liệu"  # nhận ra từ viết tắt CSDL


def test_minutes_and_full_course_name():
    q = parse("Ôn Mạng máy tính trước 8h ngày mai 90 phút", NOW, COURSES)
    assert q.deadline == datetime(2026, 11, 26, 8, 0)
    assert q.hours == 1.5
    assert q.course == "Mạng máy tính"
    assert q.title == "Ôn Mạng máy tính"


def test_time_of_day_is_not_taken_as_duration():
    q = parse("Nộp bài 23h59 ngày 05/12/2026", NOW, COURSES)
    assert q.hours == DEFAULT_HOURS
    assert q.deadline == datetime(2026, 12, 5, 23, 59)


def test_decimal_hours_and_low_priority():
    q = parse("Đọc tài liệu thứ 2 tuần sau 1,5 tiếng, không gấp", NOW)
    assert q.hours == 1.5
    assert q.priority is Priority.LOW


def test_missing_deadline_is_reported():
    q = parse("Đọc sách", NOW)
    assert q.deadline is None
    assert any("hạn nộp" in n for n in q.notes)


def test_progress_store_roundtrip(tmp_path):
    from modules.scheduler.progress import ProgressStore, block_key

    store = ProgressStore(tmp_path / "app.db")
    k = block_key("t-1", datetime(2026, 11, 25, 7, 0))
    assert store.done() == set()
    assert store.set_done(k, True) == {k}
    assert ProgressStore(tmp_path / "app.db").done() == {k}  # đọc lại từ file
    assert store.set_done(k, False) == set()
