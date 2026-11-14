"""WP-05b — Tóm tắt email học tập bằng LLM (plan_module_d.md § WP-05).

Quy tắc bảo mật ("Chặn tại cổng"):
- Nếu safety_status == MALICIOUS: Tuyệt đối không gọi LLM, trả về thông báo chặn.
- Nếu label không thuộc nhóm học tập: Trả về chuỗi rỗng "".
- Trước khi gửi cho LLM: Luôn chạy qua redact_pii() để che thông tin cá nhân.
- Tối đa 150 ký tự cho bản tóm tắt.
- Cơ chế fallback offline: Trích 2 câu đầu tiên sau khi redact nếu mất mạng hoặc lỗi API.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from core.contracts import ClassifiedEmail, EmailLabel, SafetyStatus
from core.llm_client import LLMClient, get_client
from .models import ProcessedEmail
from .redact import redact_pii

logger = logging.getLogger(__name__)

# Đảm bảo EmailLabel.COURSEWORK khả dụng nếu caller sử dụng
if not hasattr(EmailLabel, "COURSEWORK"):
    setattr(EmailLabel, "COURSEWORK", EmailLabel.ASSIGNMENT)

# Các nhãn thuộc nhóm học tập được phép tóm tắt
_STUDY_LABEL_VALUES = {"assignment", "coursework", "announcement", "schedule"}

MALICIOUS_BLOCK_MESSAGE = "Email độc hại - Đã chặn tóm tắt."


def _is_study_label(label: Any) -> bool:
    """Kiểm tra nhãn có thuộc nhóm học tập hay không."""
    if label is None:
        return False
    if isinstance(label, EmailLabel):
        return label in {
            EmailLabel.ASSIGNMENT,
            EmailLabel.ANNOUNCEMENT,
            EmailLabel.SCHEDULE,
        }
    val = getattr(label, "value", str(label)).strip().lower()
    return val in _STUDY_LABEL_VALUES


def _extract_first_two_sentences(text: str, max_chars: int = 150) -> str:
    """Fallback offline: Trích 2 câu đầu tiên sau khi redact (tối đa 150 ký tự)."""
    cleaned = text.strip()
    if not cleaned:
        return ""
    # Tách câu theo dấu chấm, chấm than, hỏi chấm hoặc xuống dòng
    sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", cleaned) if s.strip()]
    if not sentences:
        result = cleaned
    elif len(sentences) == 1:
        result = sentences[0]
    else:
        result = f"{sentences[0]} {sentences[1]}"

    if len(result) > max_chars:
        result = result[: max_chars - 3].rstrip() + "..."
    return result


def summarize_email(
    subject: str | ClassifiedEmail | ProcessedEmail,
    body: str = "",
    label: EmailLabel | str | None = None,
    safety_status: SafetyStatus | str | None = None,
    client: LLMClient | None = None,
) -> str:
    """Tóm tắt email học tập bằng LLM với các biện pháp bảo vệ tại cổng.

    Args:
        subject: Tiêu đề email (hoặc đối tượng ClassifiedEmail / ProcessedEmail).
        body: Nội dung email.
        label: Nhãn phân loại email (EmailLabel hoặc string).
        safety_status: Trạng thái an toàn (SafetyStatus hoặc string).
        client: LLMClient tuỳ chọn (nếu None sẽ lấy từ core.llm_client.get_client).

    Returns:
        Chuỗi tóm tắt <= 150 ký tự, hoặc "" nếu không phải email học tập,
        hoặc thông báo chặn nếu là MALICIOUS.
    """
    # 1. Hỗ trợ truyền đối tượng email
    if isinstance(subject, ClassifiedEmail):
        body = subject.body
        label = subject.label
        safety_status = subject.safety
        subject = subject.subject
    elif isinstance(subject, ProcessedEmail):
        body = subject.email.body
        label = subject.email.label
        safety_status = subject.email.safety
        subject = subject.email.subject
    else:
        subject = str(subject or "")

    # Mặc định safety_status nếu chưa truyền
    if safety_status is None:
        safety_status = SafetyStatus.SAFE
    elif isinstance(safety_status, str):
        try:
            safety_status = SafetyStatus(safety_status.lower())
        except ValueError:
            safety_status = SafetyStatus.SUSPICIOUS

    # Mặc định label nếu chưa truyền
    if label is None:
        label = EmailLabel.OTHER
    elif isinstance(label, str):
        label_lower = label.lower().strip()
        if label_lower in ("assignment", "coursework"):
            label = EmailLabel.ASSIGNMENT
        elif label_lower == "announcement":
            label = EmailLabel.ANNOUNCEMENT
        elif label_lower == "schedule":
            label = EmailLabel.SCHEDULE
        elif label_lower == "phishing":
            label = EmailLabel.PHISHING
        elif label_lower == "spam":
            label = EmailLabel.SPAM
        else:
            label = EmailLabel.OTHER

    # 2. Quy tắc chặn tại cổng: MALICIOUS tuyệt đối không gọi LLM
    if safety_status == SafetyStatus.MALICIOUS:
        return MALICIOUS_BLOCK_MESSAGE

    # 3. Chỉ tóm tắt email học tập (COURSEWORK/ASSIGNMENT, ANNOUNCEMENT, SCHEDULE)
    if not _is_study_label(label):
        return ""

    # 4. Che thông tin cá nhân (PII) trước khi xử lý
    redacted_subject = redact_pii(subject)
    redacted_body = redact_pii(body)

    content_for_fallback = redacted_body if redacted_body.strip() else redacted_subject

    # 5. Gọi LLM tóm tắt (có fallback offline)
    if client is None:
        client = get_client()

    prompt = (
        f"<email>\n"
        f"Tiêu đề: {redacted_subject}\n"
        f"Nội dung: {redacted_body[:800]}\n"
        f"</email>"
    )
    system = (
        "Bạn là trợ lý học tập. Hãy tóm tắt email học tập sau đây thật ngắn gọn bằng tiếng Việt. "
        "Độ dài tối đa không quá 150 ký tự. Tập trung vào môn học, deadline hoặc hành động chính cần làm."
    )

    try:
        resp = client.generate(prompt, system=system, temperature=0.0)
        summary = (resp.text or "").strip()
        # Loại bỏ code fence hoặc dấu nháy bao quanh
        summary = re.sub(r"^```(?:text|markdown)?\s*|\s*```$", "", summary).strip()
        summary = summary.strip("\"'")

        if not summary:
            return _extract_first_two_sentences(content_for_fallback)

        if len(summary) > 150:
            summary = summary[:147].rstrip() + "..."
        return summary
    except Exception as exc:
        logger.info("LLM không khả dụng hoặc lỗi (%s) - dùng offline fallback", exc)
        return _extract_first_two_sentences(content_for_fallback)
