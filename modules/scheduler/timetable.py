"""Đọc thời khoá biểu từ CSV: thu,bat_dau,ket_thuc,mon,phong."""
from __future__ import annotations

import csv
import io
from datetime import datetime, time
from pathlib import Path
from typing import IO

from .model import ClassSession

REQUIRED = ("thu", "bat_dau", "ket_thuc", "mon")


def _weekday(raw: str) -> int:
    value = raw.strip().upper()
    if value in ("CN", "8"):
        return 6
    n = int(value)
    if not 2 <= n <= 7:
        raise ValueError(f"thứ '{raw}' không hợp lệ (2–7 hoặc CN)")
    return n - 2


def _time(raw: str) -> time:
    value = raw.strip().lower().replace("h", ":")
    if value.endswith(":"):
        value += "00"
    return datetime.strptime(value, "%H:%M").time()


def load_timetable_csv(source: str | Path | IO) -> tuple[list[ClassSession], list[str]]:
    """Trả (các buổi học hợp lệ, danh sách lỗi theo dòng). Dòng lỗi bị bỏ qua."""
    if isinstance(source, (str, Path)):
        text = Path(source).read_text(encoding="utf-8-sig")
    else:
        raw = source.read()
        text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw

    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    missing = [c for c in REQUIRED if c not in headers]
    if missing:
        return [], [f"Thiếu cột: {', '.join(missing)} (cần {','.join(REQUIRED)},phong)"]

    sessions, errors = [], []
    for line_no, row in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        if not any(row.values()):
            continue
        try:
            sessions.append(ClassSession(
                weekday=_weekday(row["thu"]), start=_time(row["bat_dau"]),
                end=_time(row["ket_thuc"]), course=row["mon"], room=row.get("phong", "")))
        except ValueError as e:
            errors.append(f"Dòng {line_no}: {e}")
    return sessions, errors
