"""Publish D-approved messages and documents to shared Streamlit session state."""

from __future__ import annotations

from pathlib import Path
from typing import MutableMapping, Any

from core.contracts import SafetyStatus
from .models import ProcessedEmail
from .safety import can_forward_email


def publish_to_modules(
    processed: ProcessedEmail, state: MutableMapping[str, Any]
) -> bool:
    """Publish a user-approved email to B and its gated attachments to A.

    Returns False without mutating state if the email fails the forwarding gate.
    ``verified_emails`` and ``safe_attachments`` are keyed by stable IDs/hashes.
    """
    email = processed.email
    if email.safety is SafetyStatus.MALICIOUS:
        return False
    if not can_forward_email(email, user_approved=processed.user_approved):
        return False

    state.setdefault("verified_emails", {})[email.id] = email
    state.setdefault("verified_email_ids", set()).add(email.id)
    if email.safety is SafetyStatus.SUSPICIOUS:
        state.setdefault("approved_suspicious_email_ids", set()).add(email.id)

    attachments = state.setdefault("safe_attachments", {})
    documents = state.setdefault("verified_documents", {})
    for attachment in processed.safe_attachments:
        attachments[attachment.sha256] = attachment
        if attachment.sha256 in documents:
            continue
        path = Path(attachment.path)
        if path.suffix.lower() not in {".pdf", ".txt", ".md"}:
            continue
        from modules.qa.loader import load_document_bytes

        try:
            documents[attachment.sha256] = load_document_bytes(
                path.name, path.read_bytes()
            )
        except Exception:
            # Parsing errors stay at the A boundary; D can still deliver the email to B.
            continue
    return True
