"""Mô hình dữ liệu nội bộ Module D (plan_module_d.md § 5).

Dùng SafetyStatus / EmailLabel từ core.contracts — KHÔNG định nghĩa lại.
Các dataclass ở đây chỉ dùng trong modules/email_security/; không xuất ra
ngoài qua API công khai của module (ngoại trừ ProcessedEmail).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.contracts import (
    ClassifiedEmail,
    EmailLabel,  # re-export tiện dùng trong module  # noqa: F401
    SafeAttachment,
    SafetyStatus,  # re-export tiện dùng trong module  # noqa: F401
)


@dataclass(frozen=True)
class Reason:
    """Một lý do cụ thể dẫn đến quyết định an toàn.

    ``code`` ổn định (dùng trong test và UI để lọc/hiển thị);
    ``message`` bằng tiếng Việt cho người dùng cuối.
    """

    code: str    # vd "URL_SHORTENER", "LOOKALIKE_DOMAIN", "VT_MALICIOUS", "MAGIC_MISMATCH"
    message: str  # vd "URL rút gọn — không rõ đích đến thực sự"


@dataclass(frozen=True)
class Reputation:
    """Kết quả tra cứu từ VirusTotal (hoặc bản giả khi offline).

    ``status=None`` nghĩa là UNKNOWN (hash/URL không có trên VT hoặc lỗi mạng).
    ``error`` ghi lý do kỹ thuật: "not_found", "quota", "network", "no_key", "rate_limited".
    """

    status: SafetyStatus | None = None   # None = UNKNOWN
    malicious: int = 0
    suspicious: int = 0
    source: str = "virustotal"
    error: str | None = None


@dataclass
class UrlFinding:
    """Kết quả quét một URL đơn lẻ."""

    url: str            # URL gốc (đã chuẩn hoá)
    defanged: str       # URL defang để hiển thị an toàn, vd "hxxp://evil[.]com"
    status: SafetyStatus
    reasons: list[Reason] = field(default_factory=list)
    reputation: Reputation | None = None


@dataclass
class AttachmentFinding:
    """Kết quả quét một file đính kèm."""

    filename: str       # tên file đã làm sạch (không có path traversal)
    path: str           # đường dẫn tương đối sau khi lưu (vd "data/real/e-001/abc123_file.pdf")
    sha256: str         # 64 ký tự hex lowercase
    size: int           # kích thước byte sau khi giải mã từ email
    status: SafetyStatus
    reasons: list[Reason] = field(default_factory=list)
    reputation: Reputation | None = None


@dataclass
class ParsedEmail:
    """Kết quả parse .eml thô — dữ liệu trung gian nội bộ, chưa gán nhãn.

    Chỉ dùng trong pipeline.py; không xuất ra ngoài module.
    """

    message_id: str         # Từ header Message-ID (hoặc UUID4 nếu thiếu)
    sender: str             # Header From: (địa chỉ đã parse)
    subject: str
    received_at: object     # datetime (timezone-aware nếu có, UTC nếu không)
    body_text: str          # Văn bản thuần (ưu tiên text/plain, fallback strip HTML)
    urls: list[str]         # Tất cả URL trong body + href
    html_links: list[tuple[str, str]]  # [(link_text, href)] từ thẻ <a>
    reply_to: str | None    # Header Reply-To (None nếu không có)
    auth_results: str | None  # Header Authentication-Results (None nếu không có)
    raw_attachments: list[dict]  # [{"filename": str, "content": bytes, "mimetype": str}]


@dataclass
class ProcessedEmail:
    """Kết quả đầy đủ của pipeline Module D.

    ``email`` và ``safe_attachments`` là dữ liệu theo contract → gửi cho B và A.
    Các trường còn lại là chi tiết nội bộ → dùng cho UI và logging.
    """

    email: ClassifiedEmail                   # Gửi cho Module B
    safe_attachments: list[SafeAttachment]   # Gửi cho Module A (chỉ file SAFE / đã duyệt)
    url_findings: list[UrlFinding]
    attachment_findings: list[AttachmentFinding]
    sender_reasons: list[Reason]
    classifier_method: str                   # "tfidf" | "llm" | "llm+tfidf" | "fallback" | "stub"
    can_forward: bool
    user_approved: bool = False
