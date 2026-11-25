"""Bộ trích xuất dự phòng chạy bằng luật, dùng khi chưa có khóa LLM (nguyên tắc V: chạy được
trên máy lạ).

``RuleBasedLLM`` có cùng giao diện ``generate()`` với ``core.llm_client.LLMClient``: đọc phần
``<source>…</source>`` cuối cùng trong prompt và trả JSON đúng schema ``ExtractionResult``. Vì vậy
mọi bước sau của module B (kiểm chứng câu trích, chuẩn hoá ngày giờ, so khớp, phát hiện dời hạn)
chạy y như với LLM thật. Mọi câu trích là chuỗi con nguyên văn của nguồn.

Độ phủ thấp hơn LLM: chỉ nhận ra hạn nộp mà bộ chuẩn hoá ngày giờ đọc được, tên bài lấy từ tiêu
đề hoặc dòng đầu tài liệu. Độ tin cậy vì thế thấp hơn và người dùng vẫn phải xác nhận.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from core import clock
from core.llm_client import LLMResponse
from modules.extraction.datetime_normalizer import normalize

EXTENSION = re.compile(r"\b(dời|lùi|gia|đổi)\s+hạn\b", re.I)
ASSIGNMENT_HINT = re.compile(
    r"\b(bài tập|bài tập lớn|báo cáo|đồ án|tiểu luận|project|assignment|nộp|hạn nộp|deadline|bài kiểm tra|quiz)\b",
    re.I)
PLATFORM = re.compile(r"\b(?:trên|qua|lên)\s+((?:LMS|Google Drive|Google Classroom|Classroom|Teams|Moodle|email)"
                      r"(?: của trường| lớp)?)", re.I)
FORMATS = re.compile(r"\.(pdf|zip|rar|docx?|pptx?|ipynb|py)\b|\b(PDF|ZIP|Word)\b")
NAMING = re.compile(r"đặt tên(?: file)?(?: là| theo)?\s+([\w.\-]+_[\w.\-]+)", re.I)
CRITERIA = re.compile(r"Tiêu chí chấm(?: điểm)?\s*:\s*([^\n]+)", re.I)
TAG = re.compile(r"^\s*\[([^\]]{1,20})\]")


def _source(prompt: str) -> str:
    """Khối dữ liệu là ``<source>`` cuối cùng đứng riêng một dòng (lời dặn bảo mật trong prompt
    cũng nhắc tới "<source>...</source>" ngay trong câu, nên không lấy theo cặp thẻ đầu tiên)."""
    start = prompt.rfind("<source>\n")
    end = prompt.rfind("\n</source>")
    return prompt[start + len("<source>\n"):end] if 0 <= start < end else ""


def _sentences(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        out += [s.strip() for s in re.split(r"(?<=[.!?;])\s+", line) if s.strip()]
    return out


def _ev(quote: str, location: str) -> dict:
    return {"quote": quote, "location": location}


def _field(value, quote: str | None, location: str) -> dict:
    return {"value": value, "evidence": _ev(quote, location) if quote else None}


class RuleBasedLLM:
    provider = "rules"
    model = "rules-v1"

    def __init__(self, anchor: datetime | None = None):
        self.anchor = anchor or clock.now()

    def is_configured(self) -> bool:
        return True

    def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.0,
                 **_: object) -> LLMResponse:
        return LLMResponse(text=json.dumps(self.extract(_source(prompt)), ensure_ascii=False))

    # ------------------------------------------------------------------ luật
    def extract(self, src: str) -> dict:
        is_email = src.startswith("Người gửi:")
        if is_email:
            m = re.search(r"^Tiêu đề:\s*(.*)$", src, re.M)
            subject = m.group(1).strip() if m else ""
            body = src.split("Nội dung:", 1)[-1]
            pages = [("email", body)]
        else:
            subject = ""
            pages = [(f"p{n}", t) for n, t in re.findall(r"--- TRANG (\d+) ---\n(.*?)(?=\n\n--- TRANG |\Z)",
                                                          src, re.S)] or [("p1", src)]

        deadlines = []
        for loc, text in pages:
            for s in _sentences(text):
                if not re.search(r"\d|mai|tuần|thứ|chủ nhật", s, re.I):
                    continue
                nd = normalize(s, self.anchor)
                if nd.value is not None:
                    deadlines.append({"label": None, "raw_text": s, "evidence": _ev(s, loc)})
        whole = "\n".join(t for _, t in pages)
        if not deadlines and not ASSIGNMENT_HINT.search(subject + "\n" + whole):
            return {"assignments": [], "not_assignment": True}
        if not deadlines:
            return {"assignments": [], "not_assignment": True}

        rows = self._table_rows(pages) if not is_email else []
        if len(rows) >= 2:  # bảng lịch nộp (Excel/Word/CSV): mỗi dòng có hạn là một nhiệm vụ
            return {"assignments": [self._row_assignment(loc, row) for loc, row in rows],
                    "not_assignment": False}

        loc0 = pages[0][0]
        title_src = subject or next((s for s in _sentences(pages[0][1]) if len(s) > 6), "")
        title = TAG.sub("", title_src).strip(" -:")
        title_quote = title if title and title in src else None
        tag = TAG.match(subject)
        extension = bool(EXTENSION.search(subject + " " + whole))
        refers_to = EXTENSION.sub("", title).strip(" -:") if extension else None

        plat = PLATFORM.search(whole)
        fmts = sorted({(m.group(1) or m.group(2)).lower() for m in FORMATS.finditer(whole)})
        fmt_quote = next((s for s in _sentences(whole) if FORMATS.search(s)), None)
        naming = NAMING.search(whole)
        crit = CRITERIA.search(whole)
        crit_items = [c.strip(" .") for c in re.split(r",|;", crit.group(1))] if crit else None

        a = {
            "title": _field(refers_to or title or None, title_quote, loc0),
            "course": _field(tag.group(1), tag.group(0).strip(), loc0) if tag else _field(None, None, loc0),
            "deadlines": deadlines[:1] if not extension else deadlines[-1:],
            "submission_platform": _field(plat.group(1), plat.group(0), loc0) if plat else _field(None, None, loc0),
            "submission_format": _field([f".{f}" if f not in ("pdf", "zip", "word") else f".{f}" for f in fmts]
                                        or None, fmt_quote, loc0),
            "naming_convention": (_field(naming.group(1).rstrip(".,;"), naming.group(0), loc0) if naming
                                  else _field(None, None, loc0)),
            "grading_criteria": _field(crit_items, crit.group(0) if crit else None, loc0),
            "estimated_hours": None,
            "priority_suggestion": None,
            "is_extension_notice": extension,
            "refers_to": refers_to,
        }
        return {"assignments": [a], "not_assignment": False}

    def _table_rows(self, pages: list[tuple[str, str]]) -> list[tuple[str, str]]:
        """Các dòng bảng (ô cách nhau bằng " | ", như bộ đọc Excel/Word/CSV xuất ra) có hạn nộp."""
        out = []
        for loc, text in pages:
            for line in text.splitlines():
                cells = [c.strip() for c in line.split(" | ")]
                if len(cells) < 2 or len(cells[0]) < 3:
                    continue
                if any(normalize(c, self.anchor).value is not None for c in cells[1:]):
                    out.append((loc, line.strip()))
        return out

    def _row_assignment(self, loc: str, row: str) -> dict:
        cells = [c.strip() for c in row.split(" | ")]
        title = cells[0]
        due = next(c for c in cells[1:] if normalize(c, self.anchor).value is not None)
        plat = next((c for c in cells[1:] if re.fullmatch(r"LMS|Google Drive|Google Classroom|Classroom|Teams|"
                                                          r"Moodle|email", c, re.I)), None)
        empty = _field(None, None, loc)
        return {
            "title": _field(title, title, loc),
            "course": empty,
            "deadlines": [{"label": None, "raw_text": due, "evidence": _ev(row, loc)}],
            "submission_platform": _field(plat, plat, loc) if plat else empty,
            "submission_format": empty,
            "naming_convention": empty,
            "grading_criteria": empty,
            "estimated_hours": None,
            "priority_suggestion": None,
            "is_extension_notice": False,
            "refers_to": None,
        }


class NoCacheRepository:
    """Bọc Repository để kết quả trích xuất bằng luật không bị ghi vào bộ nhớ đệm trích xuất.

    Bộ đệm của B khoá theo nội dung nguồn + phiên bản prompt (không theo mô hình); nếu ghi kết quả
    theo luật vào đó, lần chạy sau với LLM thật sẽ đọc lại kết quả kém hơn này.
    """

    def __init__(self, repo):
        self._repo = repo

    def get_cached_extraction(self, *args, **kwargs):
        return None

    def log_extraction(self, *args, **kwargs):
        return 0

    def __getattr__(self, name):
        return getattr(self._repo, name)
