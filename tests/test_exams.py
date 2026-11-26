from datetime import date, datetime

import pytest

from core import workspace
from db.repository import Repository
from modules.scheduler import exams
from modules.scheduler.slots import busy_intervals
from modules.scheduler.model import ScheduleSettings

TODAY = date(2026, 11, 26)
TABLE = """LỊCH THI HỌC KỲ I
STT | Môn thi | Ngày thi | Giờ | Phòng | Hình thức
1 | Cơ sở dữ liệu | 18/12/2026 | 7h30 | 301-G2 | Tự luận
2 | Xác suất thống kê | 20/12 | 13:30 - 15:00 | P.504-B | Trắc nghiệm
3 | Kinh tế chính trị | 22/12/2026 | 9h00 | 90 phút | 204-A"""


def test_table_rows_are_read_without_ai():
    rows = exams.parse_exam_text(TABLE, TODAY)
    assert [r["mon"] for r in rows] == ["Cơ sở dữ liệu", "Xác suất thống kê", "Kinh tế chính trị"]
    assert rows[0] | {} == {**rows[0], "ngay": "18/12/2026", "bat_dau": "07:30", "ket_thuc": "09:00",
                            "phong": "301-G2", "hinh_thuc": "Tự luận"}
    assert rows[1]["ngay"] == "20/12/2026" and rows[1]["ket_thuc"] == "15:00" and rows[1]["phong"] == "504-B"
    assert rows[2]["ket_thuc"] == "10:30"  # 90 phút


def test_sentence_and_year_rollover():
    rows = exams.parse_exam_text("Thi giữa kỳ Mạng máy tính ngày 05/01 lúc 8h, phòng A2-301", TODAY)
    assert len(rows) == 1
    assert rows[0]["mon"] == "Mạng máy tính" and rows[0]["ngay"] == "05/01/2027"
    assert rows[0]["bat_dau"] == "08:00" and rows[0]["phong"] == "A2-301"


def test_rows_are_validated():
    good, errors = exams.rows_to_exams([
        {"mon": "CSDL", "ngay": "18/12/2026", "bat_dau": "07:30", "ket_thuc": "", "gio_on": 3},
        {"mon": "", "ngay": "18/12/2026", "bat_dau": "07:30"},
        {"mon": "XSTK", "ngay": "32/12/2026", "bat_dau": "07:30"},
        {"mon": "Mạng", "ngay": "19/12/2026", "bat_dau": ""},
    ])
    assert len(good) == 1 and good[0].end == datetime(2026, 12, 18, 9, 0) and good[0].review_hours == 3
    assert len(errors) == 3 and "thiếu tên môn" in errors[0] and "thiếu giờ bắt đầu" in errors[2]


def test_exam_blocks_time_only_on_its_day():
    e = exams.ExamSession("CSDL", datetime(2026, 12, 18, 7, 30), datetime(2026, 12, 18, 9, 0))
    busy = busy_intervals([e], ScheduleSettings(start=date(2026, 12, 14), days=7))
    assert [(b0, b1) for b0, b1, _ in busy] == [(e.start, e.end)]


def test_save_merges_and_creates_review_task(tmp_path):
    ws = workspace.for_user("sv@gmail.com", base=tmp_path)
    found, _ = exams.rows_to_exams(exams.parse_exam_text(TABLE, TODAY))
    exams.save_exams(ws, found)
    exams.save_exams(ws, found[:1])  # lưu lại: không nhân đôi
    assert len(exams.load_exams(ws)) == 3
    repo = Repository(ws.db_path)
    ids = exams.add_review_tasks(repo, found)
    exams.add_review_tasks(repo, found)
    task = repo.get_task(ids[0])
    assert task["title"] == "Ôn thi Cơ sở dữ liệu" and task["status"] == "confirmed"
    assert task["deadline"].startswith("2026-12-18T07:30")
    assert len([t for t in repo.list_tasks() if t["id"].startswith("exam-")]) == 3
    exams.remove_exam(ws, found[0].key)
    assert len(exams.load_exams(ws)) == 2


def test_gemini_answer_is_parsed():
    def gen(data, mime, prompt):
        assert mime == "image/png" and "lịch thi" in prompt
        return '```json\n{"exams": [{"mon": "CSDL", "ngay": "18/12", "bat_dau": "07:30", "ket_thuc": "09:00"}]}\n```'
    rows = exams.read_exam_file(b"x", "image/png", gen, TODAY)
    assert rows[0]["ngay"] == "18/12/2026"


def test_gemini_error_is_friendly():
    def gen(data, mime, prompt):
        raise RuntimeError("503 UNAVAILABLE. The model is overloaded.")
    with pytest.raises(exams.ExamReadError, match="quá tải"):
        exams.read_exam_file(b"x", "image/png", gen, TODAY)
