import io
import json

import pytest

from modules.scheduler.timetable import load_timetable_csv
from modules.scheduler.timetable_image import (
    PROMPT, TimetableImageError, read_timetable_image, to_csv,
)


def fake(reply):
    seen = {}

    def gen(data, mime, prompt):
        seen.update(data=data, mime=mime, prompt=prompt)
        return reply if isinstance(reply, str) else json.dumps(reply, ensure_ascii=False)
    return gen, seen


def test_photo_becomes_timetable_rows():
    gen, seen = fake({"sessions": [
        {"thu": "2", "bat_dau": "07:00", "ket_thuc": "09:50", "mon": "Cơ sở dữ liệu", "phong": "301-G2"},
        {"thu": "CN", "bat_dau": "13:00", "ket_thuc": "14:50", "mon": "Tiếng Anh", "phong": None},
    ]})
    rows, errors = read_timetable_image(b"\xff\xd8\xff", "tkb.JPG", gen)
    assert seen["mime"] == "image/jpeg" and "tiết 1 07:00" in seen["prompt"]
    assert errors == []
    assert rows[1] == {"thu": "CN", "bat_dau": "13:00", "ket_thuc": "14:50", "mon": "Tiếng Anh", "phong": ""}
    sessions, errs = load_timetable_csv(io.StringIO(to_csv(rows)))
    assert len(sessions) == 2 and sessions[1].weekday == 6 and not errs


def test_bad_rows_are_reported_not_hidden():
    gen, _ = fake('```json\n{"sessions": [{"thu": "9", "bat_dau": "7h", "ket_thuc": "9h", "mon": "Toán"}]}\n```')
    rows, errors = read_timetable_image(b"%PDF-1.7", "tkb.pdf", gen)
    assert len(rows) == 1 and errors and "thứ" in errors[0]


def test_not_a_timetable_and_garbage():
    gen, _ = fake({"sessions": []})
    assert read_timetable_image(b"x", "meo.png", gen) == ([], [])
    gen, _ = fake("xin lỗi, tôi không đọc được")
    with pytest.raises(TimetableImageError, match="không trả về"):
        read_timetable_image(b"x", "a.png", gen)


def test_wrong_file_and_api_errors():
    gen, _ = fake({"sessions": []})
    with pytest.raises(TimetableImageError, match="Chỉ đọc được"):
        read_timetable_image(b"x", "a.docx", gen)

    def bad_key(*a):
        raise RuntimeError("400 INVALID_ARGUMENT. API key not valid.")
    with pytest.raises(TimetableImageError, match="Khóa Gemini không hợp lệ"):
        read_timetable_image(b"x", "a.png", bad_key)

    def quota(*a):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")
    with pytest.raises(TimetableImageError, match="hết lượt"):
        read_timetable_image(b"x", "a.png", quota)


def test_prompt_mentions_required_format():
    for word in ('"thu"', '"bat_dau"', '"ket_thuc"', '"mon"', '"phong"', "CN"):
        assert word in PROMPT
