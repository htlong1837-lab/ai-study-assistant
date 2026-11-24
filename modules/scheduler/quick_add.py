"""Thêm nhiệm vụ bằng một câu tiếng Việt tự nhiên, không cần LLM.

Ví dụ: "Báo cáo CSDL 23h59 thứ Sáu tuần sau, 3 giờ, gấp"
→ tên "Báo cáo CSDL", hạn 23:59 thứ Sáu tuần sau, 3 giờ, ưu tiên cao.

Hạn nộp do bộ chuẩn hoá ngày giờ của module B phân giải (modules.extraction.datetime_normalizer).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

from core.contracts import Priority
from modules.extraction.datetime_normalizer import normalize

DEFAULT_HOURS = 2.0

_HOURS = re.compile(r"(?<![\d:h])(\d+(?:[.,]\d+)?)\s*(?:giờ|tiếng|gio|tieng)(?!\s*\d)", re.I)
_MINUTES = re.compile(r"(?<![\d:h])(\d+)\s*phút", re.I)
_HIGH = re.compile(r"\b(gấp|khẩn|quan trọng|ưu tiên cao)\b|!{2,}", re.I)
_LOW = re.compile(r"\b(không gấp|nhẹ|ưu tiên thấp|thong thả)\b", re.I)
# Phần mô tả thời gian, dùng để cắt khỏi tên nhiệm vụ.
_TIME_WORDS = re.compile(
    r"\b(trước|hạn|deadline|nộp|vào|lúc|ngày|mai|ngày mai|hôm nay|tối|sáng|chiều|thứ\s*\w+|"
    r"chủ nhật|cn|tuần\s*(này|sau|tới)|\d{1,2}h\d{0,2}|\d{1,2}:\d{2}|\d{1,2}/\d{1,2}(/\d{2,4})?)\b",
    re.I)


@dataclass
class QuickTask:
    title: str
    deadline: datetime | None
    hours: float
    priority: Priority
    course: str
    notes: list[str] = field(default_factory=list)


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d")


def _title(text: str) -> str:
    head = re.split(r"[,;]", text, maxsplit=1)[0]
    m = _TIME_WORDS.search(head)
    if m and m.start() > 0:
        head = head[: m.start()]
    head = re.sub(r"\s+", " ", head).strip(" -:")
    return head or text.strip()


def parse(text: str, now: datetime, courses: list[str] | None = None) -> QuickTask:
    text = text.strip()
    notes: list[str] = []

    norm = normalize(text, now)
    deadline = norm.value.replace(tzinfo=None) if norm.value else None
    notes += norm.assumptions
    if deadline is None:
        notes.append("Chưa đọc được hạn nộp — hãy ghi rõ, ví dụ “23h59 thứ Sáu” hoặc “05/12”.")

    hours = DEFAULT_HOURS
    if m := _HOURS.search(text):
        hours = float(m.group(1).replace(",", "."))
    elif m := _MINUTES.search(text):
        hours = int(m.group(1)) / 60
    else:
        notes.append(f"Không ghi số giờ, giả định {DEFAULT_HOURS:g} giờ.")
    hours = min(max(hours, 0.5), 40.0)

    if _LOW.search(text):
        priority = Priority.LOW
    elif _HIGH.search(text):
        priority = Priority.HIGH
    else:
        priority = Priority.MEDIUM

    course = "Chung"
    folded = _fold(text)
    words = set(re.findall(r"\w+", folded))
    for name in sorted(courses or [], key=len, reverse=True):
        short = re.sub(r"\s*\(.*\)", "", name)
        acronym = "".join(w[0] for w in _fold(short).split())  # "Cơ sở dữ liệu" → "csdl"
        if _fold(short) in folded or (len(acronym) >= 2 and acronym in words):
            course = short
            break

    return QuickTask(_title(text), deadline, hours, priority, course, notes)
