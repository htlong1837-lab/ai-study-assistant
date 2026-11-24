"""Tạo bộ email mẫu cho buổi demo: python -m scripts.make_demo_emails

Sinh vào data/demo/ (email tự soạn, không phải email thật):
- 01_bai_tap_co_de.eml   giảng viên giao bài, kèm đề bài PDF
- 02_doi_han.eml         email dời hạn bài tập trên (B phải phát hiện thay đổi)
- 03_lua_dao.eml         email giả mạo phòng đào tạo, link lạ + tệp .exe đổi đuôi
"""
from __future__ import annotations

import hashlib
from email.message import EmailMessage
from pathlib import Path

import pymupdf as fitz

OUT = Path(__file__).resolve().parents[1] / "data" / "demo"

DE_BAI = """ĐỀ BÀI TẬP LỚN SỐ 2 - TRÍ TUỆ NHÂN TẠO
Yêu cầu: cài đặt thuật toán A* cho bài toán 8-puzzle, so sánh với BFS về số nút mở rộng.
Nộp: báo cáo PDF và mã nguồn nén .zip, đặt tên MSSV_HoTen_BTL2.zip.
Hạn nộp: 23h59 ngày 05/12/2026 trên LMS của trường.
Tiêu chí chấm: đúng thuật toán (4 điểm), thí nghiệm và so sánh (4 điểm), báo cáo rõ ràng (2 điểm).
"""


def _pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    # insert_htmlbox dùng font có sẵn hỗ trợ Unicode; insert_textbox với "helv" làm mất dấu tiếng Việt.
    html = "".join(f"<p>{line}</p>" for line in text.strip().splitlines())
    page.insert_htmlbox(fitz.Rect(50, 50, 550, 800), html, css="* {font-size: 11pt;}")
    data = doc.tobytes()
    doc.close()
    return data


def _mail(sender: str, subject: str, body: str, date: str) -> EmailMessage:
    m = EmailMessage()
    m["From"] = sender
    m["To"] = "sinhvien@example.edu.vn"
    m["Subject"] = subject
    m["Date"] = date
    m["Message-ID"] = f"<demo-{hashlib.sha1(subject.encode()).hexdigest()[:10]}@example.edu.vn>"
    m.set_content(body)
    return m


def build() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    m1 = _mail(
        "Giảng viên AI <gv.ai@example.edu.vn>",
        "[AI] Bài tập lớn số 2 - thuật toán A*",
        "Chào các em,\n\nThầy gửi đề bài tập lớn số 2 trong file đính kèm. "
        "Các em nộp trước 23h59 ngày 05/12/2026 trên LMS.\n\nThân mến.",
        "Mon, 23 Nov 2026 08:00:00 +0700",
    )
    m1.add_attachment(_pdf_bytes(DE_BAI), maintype="application", subtype="pdf",
                      filename="de_bai_BTL2.pdf")
    m2 = _mail(
        "Giảng viên AI <gv.ai@example.edu.vn>",
        "[AI] Dời hạn bài tập lớn số 2",
        "Chào các em,\n\nDo lịch thi giữa kỳ, hạn nộp bài tập lớn số 2 (thuật toán A*) "
        "được dời sang 23h59 ngày 12/12/2026.\n\nThân mến.",
        "Wed, 25 Nov 2026 09:30:00 +0700",
    )
    m3 = _mail(
        "Phong Dao Tao <phongdaotao@example-edu-vn.top>",
        "[KHẨN] Cập nhật tài khoản LMS trước 24h",
        "Tài khoản LMS của bạn sắp bị khoá. Đăng nhập ngay tại "
        "http://bit.ly/lms-xac-minh để xác minh, hoặc chạy tệp đính kèm.",
        "Thu, 26 Nov 2026 22:10:00 +0700",
    )
    m3.add_attachment(b"MZ\x90\x00" + b"\x00" * 60, maintype="application", subtype="pdf",
                      filename="huong_dan_xac_minh.pdf")
    paths = []
    for name, msg in (("01_bai_tap_co_de.eml", m1), ("02_doi_han.eml", m2), ("03_lua_dao.eml", m3)):
        path = OUT / name
        path.write_bytes(bytes(msg))
        paths.append(path)
    return paths


if __name__ == "__main__":
    for p in build():
        print(p)
