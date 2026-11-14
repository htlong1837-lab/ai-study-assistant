"""WP-05a — Ẩn danh thông tin cá nhân (PII) trong email.

Che các thông tin nhạy cảm trước khi gửi nội dung cho LLM hoặc hiển thị:
- Địa chỉ email -> [EMAIL]
- Số điện thoại Việt Nam -> [PHONE]
- Mã số sinh viên (MSSV) -> [STUDENT_ID]
"""
from __future__ import annotations

import re

# Email: user@domain.tld
_EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Số điện thoại Việt Nam: 03x, 05x, 07x, 08x, 09x hoặc (+84) / +84 / 84
_PHONE_REGEX = re.compile(
    r"(?:\(?\+?84\)?[\s.-]?|\b0)[35789](?:[.\-\s]?\d){8}(?!\d)"
)

# Mã số sinh viên: 8 số bắt đầu bằng 20-24 (20xxxxxx - 24xxxxxx) hoặc 2 chữ cái + 6 số
_STUDENT_ID_REGEX = re.compile(
    r"\b(?:2[0-4]\d{6}|[A-Za-z]{2}\d{6})\b"
)


def redact_pii(text: str) -> str:
    """Thay thế thông tin cá nhân (email, SĐT, MSSV) bằng các placeholder an toàn.

    Thứ tự thực hiện:
    1. Email -> [EMAIL] (tránh việc MSSV/SĐT trong email bị nhận diện nhầm)
    2. Phone -> [PHONE]
    3. MSSV  -> [STUDENT_ID]

    Args:
        text: Chuỗi văn bản cần che PII.

    Returns:
        Chuỗi văn bản đã được che các thông tin PII.
    """
    if not text:
        return ""

    # 1. Che email
    result = _EMAIL_REGEX.sub("[EMAIL]", text)

    # 2. Che số điện thoại
    result = _PHONE_REGEX.sub("[PHONE]", result)

    # 3. Che MSSV
    result = _STUDENT_ID_REGEX.sub("[STUDENT_ID]", result)

    return result
