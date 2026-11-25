"""Đọc thư Gmail bằng mã truy cập từ "Đăng nhập bằng Google", chỉ đọc.

Người dùng chỉ bấm nút đăng nhập; Google hỏi họ có cho phép xem thư không (quyền
``gmail.readonly``). App không bao giờ thấy mật khẩu. Mã truy cập do ``st.login`` cấp, sống khoảng
1 giờ; hết hạn thì Google trả 401 và người dùng đăng nhập lại.

Hàm chỉ trả byte thô (RFC 822) của từng thư, giống file .eml; phân loại và quét vẫn do
``process_email`` làm.
"""
from __future__ import annotations

import base64
from typing import Any

import requests

API = "https://gmail.googleapis.com/gmail/v1/users/me"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class GmailError(Exception):
    """Lỗi khi đọc Gmail, kèm lời giải thích cho người dùng."""


class TokenExpired(GmailError):
    pass


def _get(http: Any, url: str, token: str, params: dict | None = None) -> dict:
    try:
        r = http.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=20)
    except requests.RequestException as exc:
        raise GmailError("Không kết nối được tới Gmail. Kiểm tra mạng rồi thử lại.") from exc
    if r.status_code == 401:
        raise TokenExpired("Phiên đăng nhập Google đã hết hạn. Đăng nhập lại để lấy thư mới.")
    if r.status_code == 403:
        raise GmailError("Tài khoản chưa cho phép app đọc Gmail. Đăng xuất, đăng nhập lại và tích "
                         "ô cho phép xem email.")
    if r.status_code >= 400:
        raise GmailError(f"Gmail trả lỗi {r.status_code}.")
    return r.json()


def fetch_recent(token: str, *, days: int = 14, limit: int = 20, http: Any = None) -> list[bytes]:
    """Byte thô của tối đa ``limit`` thư mới nhất trong Hộp thư đến, ``days`` ngày gần đây."""
    if not token:
        raise TokenExpired("Chưa đăng nhập Google.")
    http = http or requests
    listing = _get(http, f"{API}/messages", token,
                   {"q": f"in:inbox newer_than:{int(days)}d", "maxResults": int(limit)})
    raws = []
    for m in listing.get("messages", []):
        msg = _get(http, f"{API}/messages/{m['id']}", token, {"format": "raw"})
        raw = msg.get("raw")
        if raw:
            raws.append(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
    return raws
