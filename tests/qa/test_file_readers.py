import io
import zipfile
from datetime import datetime
from email.message import EmailMessage

import pytest

from modules.qa import file_readers as fr
from modules.qa.loader import load_document_bytes

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return buf.getvalue()


def make_docx(paragraphs: list[str], table: list[list[str]] | None = None) -> bytes:
    p = "".join(f"<w:p><w:r><w:t>{t}</w:t></w:r></w:p>" for t in paragraphs)
    tbl = ""
    if table:
        rows = "".join("<w:tr>" + "".join(f"<w:tc><w:p><w:r><w:t>{c}</w:t></w:r></w:p></w:tc>" for c in r)
                       + "</w:tr>" for r in table)
        tbl = f"<w:tbl>{rows}</w:tbl>"
    return _zip({"word/document.xml": f'<w:document xmlns:w="{W_NS}"><w:body>{p}{tbl}</w:body></w:document>'})


def make_pptx(slides: list[list[str]]) -> bytes:
    files = {}
    for i, paras in enumerate(slides, start=1):
        body = "".join(f"<a:p><a:r><a:t>{t}</a:t></a:r></a:p>" for t in paras)
        files[f"ppt/slides/slide{i}.xml"] = f'<p:sld xmlns:p="x" xmlns:a="{A_NS}"><a:txBody>{body}</a:txBody></p:sld>'
    files["ppt/slides/slide10.xml"] = f'<p:sld xmlns:p="x" xmlns:a="{A_NS}"><a:p><a:r><a:t>Cuối</a:t></a:r></a:p></p:sld>'
    return _zip(files)


def make_xlsx() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Lịch nộp"
    ws.append(["Việc", "Hạn nộp", "Ghi chú"])
    ws.append(["Báo cáo SP1", datetime(2026, 12, 5, 23, 59), None])
    ws.append(["Thuyết trình", datetime(2026, 12, 12), "nhóm 3"])
    wb.create_sheet("Trống")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_docx_keeps_paragraphs_and_tables():
    pages = fr.read_pages("de.docx", make_docx(["Bài tập lớn số 3", "Nộp trên LMS"],
                                               [["Mốc", "Hạn"], ["Bản nháp", "01/12/2026"]]))
    assert pages[0].text.splitlines() == ["Bài tập lớn số 3", "Nộp trên LMS", "Mốc | Hạn", "Bản nháp | 01/12/2026"]


def test_xlsx_one_page_per_sheet_with_readable_dates():
    pages = fr.read_pages("lich.xlsx", make_xlsx())
    assert [p.number for p in pages] == [1, 2]
    assert "Trang tính: Lịch nộp" in pages[0].text
    assert "Báo cáo SP1 | 05/12/2026 23:59" in pages[0].text
    assert "Thuyết trình | 12/12/2026 | nhóm 3" in pages[0].text


def test_pptx_slides_in_numeric_order():
    pages = fr.read_pages("slide.pptx", make_pptx([["Tuần 1", "Giới thiệu"], ["Hạn nộp: 20/12"]]))
    assert [p.text for p in pages] == ["Tuần 1\nGiới thiệu", "Hạn nộp: 20/12", "Cuối"]


def test_csv_html_and_long_text():
    assert fr.read_pages("a.csv", "Việc;Hạn\nĐồ án;05/12".encode())[0].text == "Việc | Hạn\nĐồ án | 05/12"
    html = b"<html><style>p{}</style><body><h1>Th\xc3\xb4ng b\xc3\xa1o</h1><script>x()</script>" \
           b"<table><tr><td>Thi</td><td>15/12</td></tr></table></body></html>"
    assert fr.read_pages("tb.html", html)[0].text == "Thông báo\nThi | 15/12"
    pages = fr.read_pages("dai.md", "\n".join(f"dòng {i}" for i in range(100)).encode())
    assert len(pages) == 3 and pages[2].number == 3


def test_image_uses_media_reader_or_says_it_cannot():
    seen = {}

    def reader(data, mime, kind):
        seen.update(mime=mime, kind=kind)
        return "THÔNG BÁO\nNộp bài trước 23h59 ngày 05/12/2026"

    pages = fr.read_pages("anh.JPG", b"\xff\xd8\xff", media_reader=reader)
    assert seen == {"mime": "image/jpeg", "kind": "ảnh"}
    assert "05/12/2026" in pages[0].text

    pages = fr.read_pages("bai_giang.mp4", b"....", media_reader=lambda *a: None)
    assert "chưa đọc được" in pages[0].text and "Video" in pages[0].text

    def boom(*a):
        raise RuntimeError("quota")
    assert "chưa đọc được" in fr.read_pages("ghi_am.m4a", b"..", media_reader=boom)[0].text


def test_broken_and_unknown_files():
    with pytest.raises(ValueError, match="hỏng"):
        fr.read_pages("x.docx", b"not a zip")
    with pytest.raises(ValueError, match="Chưa hỗ trợ"):
        fr.read_pages("x.bin", b"abc")


def test_loader_accepts_office_files():
    doc = load_document_bytes("lich.xlsx", make_xlsx())
    assert doc.filename == "lich.xlsx" and len(doc.doc_id) == 16
    assert "05/12/2026 23:59" in doc.pages[0].text


def test_xlsx_attachment_flows_from_email_to_deadline(monkeypatch, tmp_path):
    """Email kèm Excel → D quét và chuyển tiếp → tài liệu đã đọc → bộ trích xuất ra hạn nộp."""
    monkeypatch.setenv("EMAIL_ATTACHMENTS_DIR", str(tmp_path))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    from modules.email_security import process_email
    from modules.email_security.config import get_settings
    from modules.email_security.handoff import publish_to_modules
    from modules.extraction.rule_extractor import RuleBasedLLM

    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()
    msg = EmailMessage()
    msg["From"] = "gv@uni.edu.vn"
    msg["To"] = "sv@gmail.com"
    msg["Subject"] = "[CSDL] Lịch nộp bài cuối kỳ"
    msg["Date"] = "Wed, 25 Nov 2026 08:00:00 +0700"
    msg["Message-ID"] = "<xlsx-flow@uni.edu.vn>"
    msg.set_content("Các em xem lịch nộp trong file đính kèm.")
    msg.add_attachment(make_xlsx(), maintype="application",
                       subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="lich_nop.xlsx")
    processed = process_email(msg.as_bytes())
    assert processed.safe_attachments, processed.attachment_findings
    state: dict = {}
    assert publish_to_modules(processed, state)
    (doc,) = state["verified_documents"].values()
    src = "\n\n".join(f"--- TRANG {p.number} ---\n{p.text}" for p in doc.pages)
    result = RuleBasedLLM(anchor=datetime(2026, 11, 25, 8)).extract(src)
    assert not result["not_assignment"]
    rows = [(a["title"]["value"], a["deadlines"][0]["raw_text"]) for a in result["assignments"]]
    assert rows == [("Báo cáo SP1", "05/12/2026 23:59"), ("Thuyết trình", "12/12/2026")]
    for a in result["assignments"]:  # câu trích phải là chuỗi con nguyên văn của nguồn
        assert a["deadlines"][0]["evidence"]["quote"] in src and a["title"]["evidence"]["quote"] in src
