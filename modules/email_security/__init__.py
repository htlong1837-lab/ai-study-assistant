"""Module D — Email & Bảo mật (Hoàng Minh).

API công khai:
    process_email(raw: bytes | Path, *, settings=None) -> ProcessedEmail
    approve_suspicious(processed: ProcessedEmail) -> ProcessedEmail
    process_many(raws, *, settings=None) -> list[ProcessedEmail]
    can_forward_email(email, user_approved=False) -> bool

Vào: file .eml (bytes hoặc Path).
Ra: ClassifiedEmail (cho Module B), SafeAttachment[] (cho Module A).
Chặn nội dung MALICIOUS theo nguyên tắc II (Constitution).
"""

from .models import (
    AttachmentFinding,
    ParsedEmail,
    ProcessedEmail,
    Reason,
    Reputation,
    UrlFinding,
)
from .pipeline import approve_suspicious, process_email, process_many
from .safety import aggregate_safety, can_forward_email, max_status

__all__ = [
    # Pipeline
    "process_email",
    "process_many",
    "approve_suspicious",
    # Safety
    "can_forward_email",
    "aggregate_safety",
    "max_status",
    # Models
    "ProcessedEmail",
    "ParsedEmail",
    "UrlFinding",
    "AttachmentFinding",
    "Reason",
    "Reputation",
]
