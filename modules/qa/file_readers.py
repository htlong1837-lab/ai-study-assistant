"""Đọc chữ từ mọi loại tệp đính kèm hay gặp để B trích hạn nộp và A hỏi đáp.

- Không cần AI: PDF (ở ``loader``), Word ``.docx``, Excel ``.xlsx``, PowerPoint ``.pptx``, văn bản
  ``.txt/.md/.csv/.tsv/.json``, trang web ``.html``.
- Cần khóa AI (Gemini): ảnh (chép chữ trong ảnh, ví dụ ảnh chụp bảng thông báo) và video/ghi âm
  (chép lời nói). Không có khóa thì vẫn tạo một trang ghi rõ là chưa đọc được, không bịa nội dung.

Mỗi hàm trả danh sách ``Page`` để giữ được số trang/trang tính/trang chiếu khi trích dẫn.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Callable
from datetime import date, datetime, time
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

from core.contracts import Page

TEXT_EXT = {".txt", ".md", ".csv", ".tsv", ".json"}
HTML_EXT = {".html", ".htm"}
OFFICE_EXT = {".docx", ".xlsx", ".pptx"}
IMAGE_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
              ".gif": "image/gif", ".heic": "image/heic"}
MEDIA_MIME = {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
              ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".wav": "audio/wav", ".ogg": "audio/ogg"}
READABLE_EXT = {".pdf"} | TEXT_EXT | HTML_EXT | OFFICE_EXT | set(IMAGE_MIME) | set(MEDIA_MIME)

LINES_PER_PAGE = 45
MAX_SHEET_ROWS = 2000
MAX_MEDIA_BYTES = 20 * 1024 * 1024  # giới hạn gửi thẳng cho Gemini

MediaReader = Callable[[bytes, str, str], "str | None"]  # (dữ liệu, mime, loại "ảnh"/"video") → chữ

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def kind_of(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_MIME:
        return "ảnh"
    if ext in MEDIA_MIME:
        return "video" if MEDIA_MIME[ext].startswith("video") else "ghi âm"
    return "tài liệu"


def _chunk(lines: list[str]) -> list[Page]:
    lines = [ln for ln in (s.rstrip() for s in lines) if ln.strip()]
    if not lines:
        return [Page(number=1, text="")]
    return [Page(number=i // LINES_PER_PAGE + 1, text="\n".join(lines[i:i + LINES_PER_PAGE]))
            for i in range(0, len(lines), LINES_PER_PAGE)]


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1258", "latin-1"):
        try:
            text = data.decode(enc)
            if enc != "utf-16" or text.count("\x00") == 0:
                return text
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------- văn bản
def read_text(name: str, data: bytes) -> list[Page]:
    text = _decode(data)
    ext = Path(name).suffix.lower()
    if ext in {".csv", ".tsv"}:
        delim = "\t" if ext == ".tsv" else (csv.Sniffer().sniff(text[:2048]).delimiter
                                             if text.strip() else ",")
        rows = csv.reader(io.StringIO(text), delimiter=delim)
        return _chunk([" | ".join(c.strip() for c in r if c.strip()) for r in rows])
    return _chunk(text.splitlines())


class _HTMLText(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table", "section"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
        elif tag in {"td", "th"}:
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def read_html(data: bytes) -> list[Page]:
    p = _HTMLText()
    p.feed(_decode(data))
    lines = [re.sub(r"\s+", " ", ln).strip(" |") for ln in "".join(p.parts).splitlines()]
    return _chunk(lines)


# --------------------------------------------------------------------------- Office
def read_docx(data: bytes) -> list[Page]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(f"{W}body")
    lines: list[str] = []

    def para(p) -> str:
        return "".join(t.text or "" for t in p.iter(f"{W}t"))

    for child in (body if body is not None else []):
        if child.tag == f"{W}p":
            lines.append(para(child))
        elif child.tag == f"{W}tbl":
            for tr in child.iter(f"{W}tr"):
                cells = [" ".join(para(p) for p in tc.iter(f"{W}p")).strip() for tc in tr.iter(f"{W}tc")]
                lines.append(" | ".join(c for c in cells if c))
    return _chunk(lines)


def _cell(v) -> str:
    if isinstance(v, datetime):
        return f"{v:%d/%m/%Y %H:%M}" if (v.hour, v.minute) != (0, 0) else f"{v:%d/%m/%Y}"
    if isinstance(v, date):
        return f"{v:%d/%m/%Y}"
    if isinstance(v, time):
        return f"{v:%H:%M}"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def read_xlsx(data: bytes) -> list[Page]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    pages = []
    try:
        for n, ws in enumerate(wb.worksheets, start=1):
            lines = [f"Trang tính: {ws.title}"]
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= MAX_SHEET_ROWS:
                    lines.append(f"… (còn nữa, chỉ đọc {MAX_SHEET_ROWS} dòng đầu)")
                    break
                cells = [_cell(v) for v in row if v is not None and str(v).strip()]
                if cells:
                    lines.append(" | ".join(cells))
            pages.append(Page(number=n, text="\n".join(lines)))
    finally:
        wb.close()
    return pages or [Page(number=1, text="")]


def read_pptx(data: bytes) -> list[Page]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                       key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
        pages = []
        for i, name in enumerate(names, start=1):
            root = ET.fromstring(z.read(name))
            paras = ["".join(t.text or "" for t in p.iter(f"{A}t")) for p in root.iter(f"{A}p")]
            pages.append(Page(number=i, text="\n".join(s for s in paras if s.strip())))
    return pages or [Page(number=1, text="")]


# --------------------------------------------------------------------------- ảnh, video
MEDIA_PROMPT = {
    "ảnh": ("Chép lại nguyên văn toàn bộ chữ có trong ảnh (giữ xuống dòng, ngày giờ, số liệu). Nếu ảnh "
            "không có chữ, mô tả ngắn ảnh trong 1–2 câu. Chỉ trả về văn bản thuần, không thêm lời bình."),
    "video": ("Chép lại lời nói trong video và chữ hiện trên màn hình, theo thứ tự thời gian, mỗi ý một "
              "dòng. Giữ nguyên mọi ngày giờ, hạn nộp, yêu cầu. Chỉ trả về văn bản thuần."),
    "ghi âm": ("Chép lại lời nói trong đoạn ghi âm, mỗi ý một dòng. Giữ nguyên mọi ngày giờ, hạn nộp, "
               "yêu cầu. Chỉ trả về văn bản thuần."),
}


def gemini_media_reader(data: bytes, mime: str, kind: str) -> str | None:
    """Đọc ảnh/video/ghi âm bằng Gemini nếu đã có khóa; không có thì trả ``None``."""
    from core.llm_client import get_client

    client = get_client()
    if client.provider != "gemini" or not client.is_configured() or len(data) > MAX_MEDIA_BYTES:
        return None
    return client.read_media(data, mime, MEDIA_PROMPT[kind])


def read_media(name: str, data: bytes, reader: MediaReader | None) -> list[Page]:
    ext = Path(name).suffix.lower()
    mime = IMAGE_MIME.get(ext) or MEDIA_MIME[ext]
    kind = kind_of(name)
    text = None
    if reader is not None:
        try:
            text = reader(data, mime, kind)
        except Exception:  # noqa: BLE001 — lỗi đọc bằng AI không được làm hỏng cả email
            text = None
    if text and text.strip():
        return _chunk(text.splitlines())
    note = f"[{kind.capitalize()} {Path(name).name}: chưa đọc được nội dung."
    if len(data) > MAX_MEDIA_BYTES:
        note += " Tệp lớn hơn 20 MB.]"
    else:
        note += " Cần khóa AI (Gemini) để đọc chữ hoặc lời nói trong tệp này.]"
    return [Page(number=1, text=note)]


# --------------------------------------------------------------------------- cửa chính
def read_pages(name: str, data: bytes, *, media_reader: MediaReader | None = gemini_media_reader) -> list[Page]:
    """Trang chữ của một tệp không phải PDF. Ném ``ValueError`` nếu loại tệp không hỗ trợ hoặc hỏng."""
    ext = Path(name).suffix.lower()
    try:
        if ext in TEXT_EXT:
            return read_text(name, data)
        if ext in HTML_EXT:
            return read_html(data)
        if ext == ".docx":
            return read_docx(data)
        if ext == ".xlsx":
            return read_xlsx(data)
        if ext == ".pptx":
            return read_pptx(data)
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        raise ValueError(f"Tệp {ext} bị hỏng hoặc không đúng định dạng.") from exc
    if ext in IMAGE_MIME or ext in MEDIA_MIME:
        return read_media(name, data, media_reader)
    raise ValueError(f"Chưa hỗ trợ đọc tệp {ext or 'không có đuôi'}.")
