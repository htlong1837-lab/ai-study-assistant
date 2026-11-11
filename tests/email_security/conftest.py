"""conftest.py — Fixture dùng chung cho test Module D.

Mọi fixture đều offline: không cần mạng, không cần API key.
"""
from __future__ import annotations

import socket
from pathlib import Path

import pytest

from modules.email_security.config import Settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Chặn mạng — đảm bảo test không gọi ra ngoài
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chặn mọi kết nối mạng trong suốt test.

    Nếu code gọi socket.connect → test sẽ fail ngay với lỗi rõ ràng
    thay vì treo hoặc phụ thuộc kết nối thực.
    """
    def _blocked_connect(self, address):  # type: ignore[override]
        raise ConnectionRefusedError(
            f"[TEST] Kết nối mạng bị chặn: {address}. "
            "Module D test phải chạy 100% offline."
        )

    monkeypatch.setattr(socket.socket, "connect", _blocked_connect)


# ---------------------------------------------------------------------------
# Settings offline (không có key API nào)
# ---------------------------------------------------------------------------

@pytest.fixture
def settings_offline() -> Settings:
    """Settings cho môi trường offline: không VT key, không LLM thật."""
    return Settings(
        virustotal_api_key="",
        domain_whitelist=["uni.edu.vn", "hust.edu.vn"],
        attach_max_mb=50,
        llm_provider="fake",
        url_shorteners=["bit.ly", "tinyurl.com", "t.co"],
        risky_tlds=[".top", ".xyz", ".click"],
        attachments_dir="data/real",
    )


# ---------------------------------------------------------------------------
# Helpers sinh .eml tổng hợp (không dùng email thật)
# ---------------------------------------------------------------------------

def make_plain_eml(
    subject: str = "Test subject",
    sender: str = "test@example.com",
    body: str = "Test body.",
    message_id: str = "test-001@example.com",
    reply_to: str | None = None,
) -> bytes:
    """Sinh bytes .eml văn bản thuần tối giản."""
    headers = [
        f"From: {sender}",
        "To: recipient@example.com",
        f"Subject: {subject}",
        f"Message-ID: <{message_id}>",
        "Date: Mon, 09 Nov 2026 08:00:00 +0700",
        "MIME-Version: 1.0",
        "Content-Type: text/plain; charset=utf-8",
    ]
    if reply_to:
        headers.append(f"Reply-To: {reply_to}")
    return ("\r\n".join(headers) + "\r\n\r\n" + body).encode("utf-8")


def make_html_eml(
    subject: str = "HTML Test",
    sender: str = "html@example.com",
    html_body: str = "<p>Hello</p>",
    message_id: str = "html-001@example.com",
) -> bytes:
    """Sinh bytes .eml với HTML body."""
    headers = "\r\n".join([
        f"From: {sender}",
        "To: recipient@example.com",
        f"Subject: {subject}",
        f"Message-ID: <{message_id}>",
        "Date: Mon, 09 Nov 2026 08:00:00 +0700",
        "MIME-Version: 1.0",
        "Content-Type: text/html; charset=utf-8",
    ])
    return (headers + "\r\n\r\n" + html_body).encode("utf-8")


def make_multipart_eml(
    subject: str = "With Attachment",
    sender: str = "attach@example.com",
    body: str = "See attachment.",
    attach_name: str = "report.pdf",
    attach_data: bytes = b"%PDF-1.4 fake pdf content",
    message_id: str = "multipart-001@example.com",
) -> bytes:
    """Sinh bytes .eml multipart/mixed với một file đính kèm."""
    import base64
    b64 = base64.b64encode(attach_data).decode("ascii")
    raw = (
        f"From: {sender}\r\n"
        f"To: recipient@example.com\r\n"
        f"Subject: {subject}\r\n"
        f"Message-ID: <{message_id}>\r\n"
        "Date: Mon, 09 Nov 2026 08:00:00 +0700\r\n"
        "MIME-Version: 1.0\r\n"
        'Content-Type: multipart/mixed; boundary="BOUND"\r\n'
        "\r\n"
        "--BOUND\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        f"{body}\r\n"
        "--BOUND\r\n"
        f'Content-Type: application/octet-stream\r\n'
        f'Content-Disposition: attachment; filename="{attach_name}"\r\n'
        "Content-Transfer-Encoding: base64\r\n"
        "\r\n"
        f"{b64}\r\n"
        "--BOUND--\r\n"
    )
    return raw.encode("utf-8")
