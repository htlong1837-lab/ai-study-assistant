"""Lịch thi / kiểm tra: sự kiện có ngày cụ thể (khác buổi học lặp lại hằng tuần).

- Đọc từ tệp đính kèm: bảng chữ (Excel, Word, PDF, CSV…) đọc bằng luật, không cần AI; ảnh chụp hoặc
  bảng khó thì gửi Gemini bằng khóa của người dùng. Người dùng luôn xem và sửa bảng trước khi lưu.
- Buổi thi chặn giờ trên lịch như buổi học (``ExamSession.on`` giống ``ClassSession.on``) và sinh một
  nhiệm vụ "Ôn thi …" có hạn là giờ thi, để bộ xếp lịch dành giờ ôn trước đó.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

FIELDS = ("mon", "ngay", "bat_dau", "ket_thuc", "phong", "hinh_thuc", "gio_on")
DEFAULT_MINUTES = 90
DEFAULT_REVIEW_HOURS = 4.0

PROMPT = """Tệp này là lịch thi / lịch kiểm tra của một sinh viên Việt Nam.
Liệt kê MỌI buổi thi dưới dạng JSON, đúng mẫu:
{"exams": [{"mon": "Cơ sở dữ liệu", "ngay": "18/12/2026", "bat_dau": "07:30", "ket_thuc": "09:00",
"phong": "301-G2", "hinh_thuc": "Tự luận"}]}

Quy tắc:
- "ngay": dd/mm/yyyy. Không ghi năm thì để dd/mm.
- "bat_dau", "ket_thuc": giờ 24h HH:MM. Chỉ có giờ bắt đầu và thời lượng (ví dụ 90 phút) thì tự tính giờ kết thúc.
  Ghi theo ca/tiết mà không có giờ thì để trống, không đoán.
- "mon": tên môn ngắn gọn như trong tệp. "phong", "hinh_thuc": không có thì "".
- Chỉ ghi những gì có trong tệp, không bịa. Không phải lịch thi thì trả {"exams": []}.
Chỉ trả về JSON, không giải thích."""


@dataclass(frozen=True)
class ExamSession:
    """Một buổi thi: chặn giờ trên lịch như buổi học nhưng chỉ vào đúng một ngày."""
    course: str
    start: datetime
    end: datetime
    room: str = ""
    kind: str = ""
    review_hours: float = DEFAULT_REVIEW_HOURS
    source: str = ""
    is_exam = True

    def on(self, day: date) -> tuple[datetime, datetime] | None:
        return (self.start, self.end) if self.start.date() == day else None

    @property
    def key(self) -> str:
        raw = f"{_fold(self.course)}|{self.start:%Y-%m-%dT%H:%M}"
        return hashlib.sha256(raw.encode()).hexdigest()[:10]

    def to_dict(self) -> dict:
        return {"mon": self.course, "start": self.start.isoformat(), "end": self.end.isoformat(),
                "phong": self.room, "hinh_thuc": self.kind, "gio_on": self.review_hours, "source": self.source}

    @classmethod
    def from_dict(cls, d: dict) -> ExamSession:
        return cls(str(d["mon"]), datetime.fromisoformat(d["start"]), datetime.fromisoformat(d["end"]),
                   str(d.get("phong", "")), str(d.get("hinh_thuc", "")),
                   float(d.get("gio_on", DEFAULT_REVIEW_HOURS) or 0), str(d.get("source", "")))


def _fold(text: str) -> str:
    """Chữ thường, bỏ dấu (đ → d) để so khớp từ khoá."""
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


# --------------------------------------------------------------------------- đọc bằng luật
_DATE = re.compile(r"(?<!\d)(\d{1,2})\s*[/.-]\s*(\d{1,2})(?:\s*[/.-]\s*(\d{2,4}))?(?!\d)")
_TIME = re.compile(r"(?<![\d/.-])([01]?\d|2[0-3])\s*(?:[h:g]|giờ)\s*([0-5]\d)?(?![\d/])", re.I)
_MINUTES = re.compile(r"(\d{2,3})\s*(?:phút|phut|')", re.I)
_ROOM = re.compile(r"(?:phòng|phong|p\.)\s*:?\s*([A-Za-z0-9][\w.-]*)", re.I)
_ROOM_CODE = re.compile(r"^[A-Z]?\d{2,4}\s*-\s*[A-Z0-9]{1,4}$|^[A-Z]{1,3}\d{1,2}\s*-\s*\d{2,4}$")
_KINDS = ("tự luận", "trắc nghiệm", "vấn đáp", "thực hành", "tiểu luận", "online", "trực tuyến", "báo cáo")
_NOISE = ("stt", "ngày", "ngay", "giờ", "gio", "phòng", "phong", "thứ", "ca thi", "hình thức", "ghi chú")


def _year_for(day: int, month: int, today: date) -> int:
    """Năm gần nhất ở tương lai (lịch thi luôn nói về các ngày sắp tới)."""
    try:
        d = date(today.year, month, day)
    except ValueError:
        return today.year
    return today.year + 1 if (today - d).days > 60 else today.year


def _course_of(cells: list[str]) -> str:
    best = ""
    for cell in cells:
        c = cell.strip(" :-–")
        c = re.sub(r"^(?:môn(?: thi| học)?|mon(?: thi| hoc)?|học phần|hoc phan)\s*:?\s*", "", c, flags=re.I)
        if not c or _DATE.search(c) or _TIME.fullmatch(c.strip()) or _ROOM.search(c) or _ROOM_CODE.match(c):
            continue
        low = c.lower()
        if low in _NOISE or any(low == k for k in _KINDS) or _MINUTES.fullmatch(c.strip()):
            continue
        if re.fullmatch(r"[\d\s.,'’-]+", c) or re.fullmatch(r"(?:ca|tiết|tiet)\s*\d+.*", low):
            continue
        letters = sum(ch.isalpha() for ch in c)
        if letters > sum(ch.isalpha() for ch in best):
            best = c
    return best


def parse_exam_text(text: str, today: date) -> list[dict]:
    """Các dòng lịch thi trong văn bản (mỗi dòng/hàng bảng có ngày là một buổi thi)."""
    rows: list[dict] = []
    for line in text.splitlines():
        m = _DATE.search(line)
        if not m:
            continue
        day, month = int(m.group(1)), int(m.group(2))
        if not (1 <= day <= 31 and 1 <= month <= 12):
            continue
        year = m.group(3)
        year = (int(year) + 2000 if len(year) == 2 else int(year)) if year else _year_for(day, month, today)
        rest = line[:m.start()] + " | " + line[m.end():]
        times = [(int(h), int(mm or 0)) for h, mm in _TIME.findall(rest)]
        start = f"{times[0][0]:02d}:{times[0][1]:02d}" if times else ""
        end = f"{times[1][0]:02d}:{times[1][1]:02d}" if len(times) > 1 else ""
        dur = _MINUTES.search(rest)
        if start and not end:
            minutes = int(dur.group(1)) if dur else DEFAULT_MINUTES
            t0 = datetime.combine(date.today(), time(*times[0]))
            t1 = min(t0 + timedelta(minutes=minutes), t0.replace(hour=23, minute=59))  # không sang ngày sau
            end = t1.strftime("%H:%M") if t1 > t0 else ""
        cells = [c for c in re.split(r"\s*[|\t;]\s*", line) if c.strip()]
        if len(cells) == 1:  # câu văn: bỏ ngày giờ, phòng và từ đệm, phần còn lại là tên môn
            plain = _ROOM.sub(" ", _MINUTES.sub(" ", _TIME.sub(" ", _DATE.sub(" ", line))))
            plain = re.sub(r"(?i)\b(?:kiểm tra|thi|giữa kỳ|cuối kỳ|học kỳ|môn|ngày|lúc|vào|từ|đến|thứ \w+|"
                           r"chủ nhật|sáng|chiều|tối)\b|[,.:;()–-]", " ", plain)
            cells = [re.sub(r"\s+", " ", plain).strip()]
        room = _ROOM.search(line)
        room = room.group(1) if room else next((c.strip() for c in cells if _ROOM_CODE.match(c.strip())), "")
        kind = next((k.capitalize() for k in _KINDS if k in line.lower()), "")
        course = _course_of(cells)
        if not course:
            continue
        rows.append({"mon": course, "ngay": f"{day:02d}/{month:02d}/{year}", "bat_dau": start,
                     "ket_thuc": end, "phong": room, "hinh_thuc": kind, "gio_on": DEFAULT_REVIEW_HOURS})
    return rows


# --------------------------------------------------------------------------- đọc bằng Gemini
class ExamReadError(Exception):
    pass


def read_exam_file(data: bytes, mime: str, generate, today: date) -> list[dict]:
    """Gemini đọc ảnh/PDF/văn bản lịch thi. ``generate(data, mime, prompt) -> str`` (xem timetable_image)."""
    try:
        raw = generate(data, mime, PROMPT)
    except Exception as exc:  # noqa: BLE001
        from core.gemini import friendly_error

        text = friendly_error(exc, getattr(generate, "api_key", ""))
        logging.getLogger(__name__).warning("Đọc lịch thi lỗi: %s", text)
        raise ExamReadError(text) from exc
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    try:
        data_ = json.loads(raw)
    except ValueError:
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            raise ExamReadError("Gemini không trả về dữ liệu đọc được. Thử lại hoặc dùng ảnh rõ hơn.") from None
        data_ = json.loads(m.group(0))
    items = data_.get("exams", []) if isinstance(data_, dict) else data_
    rows = []
    for r in items if isinstance(items, list) else []:
        if not isinstance(r, dict):
            continue
        ngay = str(r.get("ngay", "") or "").strip()
        m = _DATE.fullmatch(ngay)
        if m and not m.group(3):
            d, mo = int(m.group(1)), int(m.group(2))
            ngay = f"{d:02d}/{mo:02d}/{_year_for(d, mo, today)}"
        rows.append({"mon": str(r.get("mon", "") or "").strip(), "ngay": ngay,
                     "bat_dau": str(r.get("bat_dau", "") or "").strip(),
                     "ket_thuc": str(r.get("ket_thuc", "") or "").strip(),
                     "phong": str(r.get("phong", "") or "").strip(),
                     "hinh_thuc": str(r.get("hinh_thuc", "") or "").strip(), "gio_on": DEFAULT_REVIEW_HOURS})
    return rows


# --------------------------------------------------------------------------- kiểm tra, lưu
def _hm(raw: str) -> time:
    value = str(raw).strip().lower().replace("h", ":").replace("g", ":")
    if value.endswith(":"):
        value += "00"
    return datetime.strptime(value, "%H:%M").time()


def rows_to_exams(rows: list[dict], source: str = "") -> tuple[list[ExamSession], list[str]]:
    """Kiểm tra bảng người dùng đã sửa. Trả (buổi thi hợp lệ, lỗi theo dòng)."""
    exams, errors = [], []
    for i, r in enumerate(rows, start=1):
        course = str(r.get("mon", "") or "").strip()
        try:
            if not course:
                raise ValueError("thiếu tên môn")
            day = datetime.strptime(str(r.get("ngay", "")).strip(), "%d/%m/%Y").date()
            if not str(r.get("bat_dau", "") or "").strip():
                raise ValueError("thiếu giờ bắt đầu")
            start = datetime.combine(day, _hm(r["bat_dau"]))
            end_raw = str(r.get("ket_thuc", "") or "").strip()
            end = (datetime.combine(day, _hm(end_raw)) if end_raw else
                   min(start + timedelta(minutes=DEFAULT_MINUTES), datetime.combine(day, time(23, 59))))
            if end <= start:
                raise ValueError("giờ kết thúc phải sau giờ bắt đầu")
            hours = float(str(r.get("gio_on", DEFAULT_REVIEW_HOURS) or 0).replace(",", "."))
            if hours < 0 or hours > 60:
                raise ValueError("giờ ôn phải từ 0 đến 60")
        except (ValueError, KeyError) as exc:
            msg = str(exc)
            if "does not match format" in msg or "unconverted data" in msg:
                msg = "ngày phải dạng dd/mm/yyyy, giờ dạng 07:30"
            errors.append(f"Dòng {i} ({course or 'chưa có môn'}): {msg}")
            continue
        exams.append(ExamSession(course, start, end, str(r.get("phong", "") or "").strip(),
                                 str(r.get("hinh_thuc", "") or "").strip(), hours, source))
    return exams, errors


def load_exams(ws) -> list[ExamSession]:
    out = []
    for d in ws.read_state("exams", []) or []:
        try:
            out.append(ExamSession.from_dict(d))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(out, key=lambda e: e.start)


def save_exams(ws, new: list[ExamSession]) -> list[ExamSession]:
    """Gộp vào lịch thi đã lưu (cùng môn, cùng giờ thì thay bản mới). Trả toàn bộ lịch thi."""
    by_key = {e.key: e for e in load_exams(ws)}
    for e in new:
        by_key[e.key] = e
    exams = sorted(by_key.values(), key=lambda e: e.start)
    ws.write_state("exams", [e.to_dict() for e in exams])
    return exams


def remove_exam(ws, key: str) -> None:
    ws.write_state("exams", [e.to_dict() for e in load_exams(ws) if e.key != key])


def add_review_tasks(repo, exams: list[ExamSession]) -> list[str]:
    """Mỗi buổi thi có giờ ôn > 0 sinh một nhiệm vụ "Ôn thi …" đã xác nhận, hạn là giờ thi."""
    ids = []
    for e in exams:
        if e.review_hours <= 0:
            continue
        tid = f"exam-{e.key}"
        if repo.get_task(tid) is None:
            repo.create_task({"id": tid, "title": f"Ôn thi {e.course}", "course": e.course,
                              "deadline": e.start.isoformat(), "estimated_hours": e.review_hours,
                              "priority": "high", "confidence": 1.0, "status": "confirmed"})
            repo.add_sources(tid, [{"source": f"exam:{e.source or e.key}", "field": "deadline",
                                    "quote": f"Thi {e.course} {e.start:%H:%M %d/%m/%Y}", "kind": "manual"}])
        ids.append(tid)
    return ids
