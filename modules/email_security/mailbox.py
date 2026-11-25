"""Lấy thư từ hộp thư thật qua IMAP, chỉ đọc.

Dùng mật khẩu ứng dụng (Gmail: https://myaccount.google.com/apppasswords, cần bật xác minh 2 bước),
không dùng mật khẩu chính. Hộp thư mở ở chế độ ``readonly`` và lấy ``BODY.PEEK[]`` nên thư không bị
đánh dấu là đã đọc. Hàm chỉ trả về byte thô của từng thư; mọi bước phân loại, quét link và tệp vẫn
do ``process_email`` làm như với file .eml tải lên. Không lưu mật khẩu xuống đĩa.
"""
from __future__ import annotations

import imaplib
from collections.abc import Callable
from datetime import date, timedelta

from core import clock

# Nhà cung cấp cho phép đăng nhập IMAP bằng mật khẩu ứng dụng. Outlook/Hotmail cá nhân đã bỏ
# kiểu đăng nhập này (chỉ còn OAuth) nên không có trong danh sách.
IMAP_HOSTS = {
    "gmail.com": "imap.gmail.com",
    "googlemail.com": "imap.gmail.com",
    "yahoo.com": "imap.mail.yahoo.com",
    "icloud.com": "imap.mail.me.com",
    "me.com": "imap.mail.me.com",
}
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class MailboxError(Exception):
    """Lỗi kết nối hoặc đăng nhập, kèm lời giải thích cho người dùng."""


def imap_host(address: str) -> str | None:
    """Máy chủ IMAP đoán từ tên miền; ``None`` nếu không biết (ví dụ email trường dùng Google
    Workspace: khi đó người dùng điền ``imap.gmail.com``)."""
    domain = address.rpartition("@")[2].strip().lower()
    return IMAP_HOSTS.get(domain)


def imap_date(d: date) -> str:
    """Ngày theo định dạng IMAP (``25-Nov-2026``), không phụ thuộc locale của máy."""
    return f"{d.day:02d}-{_MONTHS[d.month - 1]}-{d.year}"


def fetch_recent(address: str, app_password: str, *, host: str | None = None, days: int = 14,
                 limit: int = 20, today: date | None = None,
                 connect: Callable[..., imaplib.IMAP4] | None = None) -> list[bytes]:
    """Byte thô của tối đa ``limit`` thư mới nhất trong Hộp thư đến, ``days`` ngày gần đây."""
    address = address.strip()
    host = (host or "").strip() or imap_host(address)
    if not host:
        raise MailboxError("Chưa biết máy chủ IMAP của tên miền này. Nếu email trường dùng Gmail, "
                           "điền máy chủ là imap.gmail.com.")
    if not address or not app_password:
        raise MailboxError("Cần nhập địa chỉ email và mật khẩu ứng dụng.")
    connect = connect or (lambda h: imaplib.IMAP4_SSL(h, timeout=20))
    try:
        conn = connect(host)
    except OSError as exc:
        raise MailboxError(f"Không kết nối được tới {host}: {exc}") from exc
    try:
        try:
            conn.login(address, app_password.replace(" ", ""))
        except imaplib.IMAP4.error as exc:
            raise MailboxError("Đăng nhập không thành công. Kiểm tra địa chỉ email và mật khẩu ứng dụng "
                               "(không phải mật khẩu đăng nhập thường).") from exc
        status, _ = conn.select("INBOX", readonly=True)
        if status != "OK":
            raise MailboxError("Không mở được Hộp thư đến.")
        since = imap_date((today or clock.today()) - timedelta(days=days))
        status, data = conn.search(None, "SINCE", since)
        if status != "OK":
            raise MailboxError("Máy chủ từ chối lệnh tìm thư.")
        ids = (data[0] or b"").split()[-limit:]
        raws: list[bytes] = []
        for msg_id in reversed(ids):  # mới nhất trước
            status, parts = conn.fetch(msg_id, "(BODY.PEEK[])")
            if status != "OK":
                continue
            raws += [p[1] for p in parts if isinstance(p, tuple) and len(p) > 1 and p[1]]
        return raws
    except imaplib.IMAP4.error as exc:
        raise MailboxError(f"Lỗi IMAP: {exc}") from exc
    finally:
        try:
            conn.logout()
        except Exception:  # noqa: BLE001 — đóng kết nối là việc phụ, không che lỗi chính
            pass
