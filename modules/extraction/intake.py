"""Cạnh nối D → B: lấy email và tài liệu mà module D đã chuyển sang.

D (``modules.email_security.handoff.publish_to_modules``) ghi vào ``st.session_state``:
- ``verified_emails``: {email_id: ClassifiedEmail} — email người dùng đã cho chuyển tiếp.
- ``approved_suspicious_email_ids``: id các email SUSPICIOUS người dùng đã duyệt.
- ``verified_documents``: {sha256: ParsedDocument} — tệp đính kèm an toàn A đã đọc.

Email SUSPICIOUS đã duyệt phải được gọi với ``allow_suspicious=True``, nếu không cổng
``ensure_safe`` của B sẽ chặn (nguyên tắc II). MALICIOUS không bao giờ đi qua.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from core.contracts import ClassifiedEmail, ParsedDocument


@dataclass
class Intake:
    emails: list[ClassifiedEmail]
    documents: list[ParsedDocument]
    approved_suspicious: set[str] = field(default_factory=set)
    from_d: bool = False  # False: chưa có gì từ D, đang dùng dữ liệu mẫu
    doc_email: dict[str, ClassifiedEmail] = field(default_factory=dict)  # doc_id → email chứa tệp

    def linked_email(self, doc: ParsedDocument) -> ClassifiedEmail | None:
        return self.doc_email.get(doc.doc_id)

    def allow_suspicious(self, email: ClassifiedEmail) -> bool:
        return email.id in self.approved_suspicious


def intake_from_d(state: Mapping[str, Any], mock_emails, mock_documents) -> Intake:
    """Email/tài liệu D đã chuyển; nếu D chưa chuyển gì thì dùng dữ liệu mẫu (gọi lười)."""
    emails = list(state.get("verified_emails", {}).values())
    from modules.email_security.purpose import allows

    # Chỉ tệp người dùng đã duyệt là "Bài tập / hạn nộp" ở Hộp thư.
    documents = [d for sha, d in (state.get("verified_documents", {}) or {}).items()
                 if allows(state, sha, "extraction")]
    if emails or documents:
        by_id = {e.id: e for e in emails}
        attachments = state.get("safe_attachments", {}) or {}
        doc_email = {}
        for sha, doc in (state.get("verified_documents", {}) or {}).items():
            if not allows(state, sha, "extraction"):
                continue
            att = attachments.get(sha) if isinstance(attachments, dict) else None
            if att is not None and att.email_id in by_id:
                doc_email[doc.doc_id] = by_id[att.email_id]
        return Intake(emails, documents, set(state.get("approved_suspicious_email_ids", set())), True,
                      doc_email)
    return Intake(list(mock_emails()), list(mock_documents()))
