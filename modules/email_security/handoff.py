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


def verified_email_batches(state: MutableMapping[str, Any]) -> list[tuple[Any, bool]]:
    """Return only emails accepted by D's gate, paired with approval status."""
    from .safety import can_forward_email

    approved = state.get("approved_suspicious_email_ids", set())
    emails = state.get("verified_emails", {})
    values = emails.values() if isinstance(emails, dict) else emails
    result = []
    for email in values:
        allow_suspicious = email.id in approved
        if can_forward_email(email, user_approved=allow_suspicious):
            result.append((email, allow_suspicious))
    return result


def verified_document_batches(state: MutableMapping[str, Any]) -> list[tuple[Any, Any]]:
    """Return parsed documents only when a matching D-approved SafeAttachment exists."""
    attachments = state.get("safe_attachments", {})
    documents = state.get("verified_documents", {})
    if not isinstance(attachments, dict) or not isinstance(documents, dict):
        return []
    return [
        (attachments[sha], document)
        for sha, document in documents.items()
        if sha in attachments and attachments[sha].sha256 == sha
    ]
