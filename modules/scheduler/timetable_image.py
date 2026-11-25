"""Đọc thời khoá biểu từ ảnh chụp hoặc PDF bằng Gemini (gọi thẳng API với khóa của người dùng).

Gemini nhìn ảnh và trả JSON các buổi học; kết quả được đổi sang đúng định dạng CSV của
``timetable.load_timetable_csv`` (thu,bat_dau,ket_thuc,mon,phong) và kiểm tra lại bằng chính hàm đó,
nên buổi nào sai định dạng sẽ hiện lỗi thay vì lặng lẽ vào lịch. Người dùng xem, sửa rồi mới lưu.
"""
from __future__ import annotations

import csv
import io
import json
import re
from collections.abc import Callable
from pathlib import Path

from .timetable import load_timetable_csv

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
        ".heic": "image/heic", ".pdf": "application/pdf"}
MAX_BYTES = 15 * 1024 * 1024
FIELDS = ("thu", "bat_dau", "ket_thuc", "mon", "phong")

PROMPT = """Ảnh/tệp này là thời khoá biểu học tập của một sinh viên Việt Nam.
Liệt kê MỌI buổi học lặp lại hằng tuần dưới dạng JSON, đúng mẫu:
{"sessions": [{"thu": "2", "bat_dau": "07:00", "ket_thuc": "09:50", "mon": "Cơ sở dữ liệu", "phong": "301-G2"}]}

Quy tắc:
- "thu": "2" đến "7" cho Thứ Hai đến Thứ Bảy, "CN" cho Chủ nhật.
- "bat_dau", "ket_thuc": giờ 24h dạng HH:MM.
- Nếu thời khoá biểu ghi theo TIẾT mà không ghi giờ, đổi theo bảng: tiết 1 07:00–07:50, 2 08:00–08:50,
  3 09:00–09:50, 4 10:00–10:50, 5 11:00–11:50, 6 13:00–13:50, 7 14:00–14:50, 8 15:00–15:50,
  9 16:00–16:50, 10 17:00–17:50, 11 18:00–18:50, 12 19:00–19:50 (ví dụ "tiết 1-3" là 07:00–09:50).
  Nếu ảnh có bảng giờ tiết riêng thì dùng bảng trong ảnh.
- "mon": tên môn ngắn gọn như trong ảnh (bỏ mã lớp nếu tên môn đã rõ). "phong": phòng học, không có thì "".
- Một môn học nhiều buổi trong tuần thì mỗi buổi là một phần tử.
- Chỉ ghi những gì thấy trong ảnh, không đoán thêm môn. Không phải thời khoá biểu thì trả {"sessions": []}.
Chỉ trả về JSON, không giải thích."""

Generate = Callable[[bytes, str, str], str]  # (dữ liệu, mime, lời dặn) → văn bản trả về


class TimetableImageError(Exception):
    pass


def mime_of(filename: str) -> str | None:
    return MIME.get(Path(filename).suffix.lower())


def gemini_generate(api_key: str, model: str = "gemini-2.5-flash") -> Generate:
    """Hàm gọi Gemini trực tiếp bằng khóa của người dùng (không qua bộ đệm chung của app)."""
    def _call(data: bytes, mime: str, prompt: str) -> str:
        from google import genai
        from google.genai import types

        from core.gemini import call_with_fallback

        client = genai.Client(api_key=api_key)

        def one(m: str) -> str:
            resp = client.models.generate_content(
                model=m,
                contents=[types.Part.from_bytes(data=data, mime_type=mime), prompt],
                config=types.GenerateContentConfig(temperature=0.0, response_mime_type="application/json"),
            )
            return resp.text or ""
        return call_with_fallback(client, model, one, key_id=str(hash(api_key)))
    _call.api_key = api_key  # để che khóa trong thông báo lỗi
    return _call


def _json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        data = json.loads(text)
    except ValueError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise TimetableImageError("Gemini không trả về dữ liệu đọc được. Thử lại hoặc chụp rõ hơn.") from None
        data = json.loads(m.group(0))
    if isinstance(data, list):
        data = {"sessions": data}
    return data


def to_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: str(r.get(k, "") or "").strip() for k in FIELDS})
    return buf.getvalue()


def read_timetable_image(data: bytes, filename: str, generate: Generate) -> tuple[list[dict], list[str]]:
    """Trả (các dòng thời khoá biểu, lỗi). Dòng là dict thu/bat_dau/ket_thuc/mon/phong."""
    mime = mime_of(filename)
    if mime is None:
        raise TimetableImageError("Chỉ đọc được ảnh PNG, JPG, WEBP, HEIC hoặc tệp PDF.")
    if not data or len(data) > MAX_BYTES:
        raise TimetableImageError("Tệp rỗng hoặc lớn hơn 15 MB.")
    try:
        raw = generate(data, mime, PROMPT)
    except Exception as exc:  # noqa: BLE001 — lỗi mạng/khóa: báo gọn cho người dùng
        from core.gemini import friendly_error

        raise TimetableImageError(friendly_error(exc, getattr(generate, "api_key", ""))) from exc
    rows = [r for r in _json(raw).get("sessions", []) if isinstance(r, dict)]
    rows = [{k: str(r.get(k, "") or "").strip() for k in FIELDS} for r in rows]
    _, errors = load_timetable_csv(io.StringIO(to_csv(rows)))
    return rows, errors
