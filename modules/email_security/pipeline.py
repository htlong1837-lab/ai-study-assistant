"""Pipeline tích hợp Module D — WP-00 stub + WP-01 (plan_module_d.md § 4).

Thứ tự pipeline (xem plan § 4):
  1. parse_eml()
  2. Lưu file đính kèm (đã làm trong parser)
  3. Quét offline (stub ở WP-00: bỏ qua, sẽ hoàn thiện WP-06, WP-08)
  4. Quét online (stub: bỏ qua)
  5. aggregate_safety (từ kết quả scanner — ở stub: SAFE)
  6. classify (stub: EmailLabel.OTHER, confidence 0.0)
  7. aggregate_safety với nhãn
  8. summarize (stub: None)
  9. Dựng ClassifiedEmail + SafeAttachment
  10. can_forward

Khi WP-06, WP-08 hoàn thành, thay thế phần stub bằng import thực.
Classifier thực và summarizer thực tương tự.
"""
from __future__ import annotations

import logging
from datetime import timezone
from pathlib import Path

from core.contracts import ClassifiedEmail, EmailLabel, SafeAttachment, SafetyStatus

from .config import Settings, get_settings
from .models import (
    AttachmentFinding,
    ParsedEmail,
    ProcessedEmail,
    Reason,
    UrlFinding,
)
from .parser import SavedAttachment, parse_eml
from .safety import aggregate_safety, can_forward_email, max_status

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Classifier stub (WP-00) — sẽ được thay bằng WP-02b/03
# ---------------------------------------------------------------------------

def _stub_classify(parsed: ParsedEmail) -> tuple[EmailLabel, float]:
    """Stub phân loại: luôn trả OTHER với confidence 0.0 để pipeline chạy được ngay."""
    return EmailLabel.OTHER, 0.0


# ---------------------------------------------------------------------------
# Scanner stubs (WP-00) — sẽ được thay bằng WP-06, WP-08
# ---------------------------------------------------------------------------

def _stub_scan_urls(
    urls: list[str],
    html_links: list[tuple[str, str]],
    sender: str,
    settings: Settings,
) -> tuple[list[UrlFinding], list[Reason]]:
    """Stub quét URL: trả rỗng (không phát hiện gì) để pipeline đi tiếp."""
    findings = [
        UrlFinding(
            url=u,
            defanged=u,  # chưa defang — sẽ dùng urls.defang_url() ở WP-06
            status=SafetyStatus.SAFE,
            reasons=[],
            reputation=None,
        )
        for u in urls
    ]
    return findings, []  # (url_findings, sender_reasons)


def _stub_scan_attachments(
    saved: list[SavedAttachment],
    settings: Settings,
) -> list[AttachmentFinding]:
    """Stub quét file đính kèm: đánh SAFE tất cả để pipeline đi tiếp."""
    return [
        AttachmentFinding(
            filename=sa.filename,
            path=sa.path,
            sha256=sa.sha256,
            size=sa.size,
            status=SafetyStatus.SAFE,
            reasons=[],
            reputation=None,
        )
        for sa in saved
    ]


# ---------------------------------------------------------------------------
# Pipeline chính
# ---------------------------------------------------------------------------

def process_email(
    raw: bytes | Path,
    *,
    settings: Settings | None = None,
) -> ProcessedEmail:
    """Pipeline tích hợp Module D: bytes .eml → ProcessedEmail.

    Đây là API công khai duy nhất mà Module B, Module A và UI gọi.

    Args:
        raw: Nội dung .eml dưới dạng bytes, hoặc Path đến file .eml.
        settings: Cấu hình. None → tự đọc từ .env qua get_settings().

    Returns:
        ProcessedEmail với ClassifiedEmail (cho B) và SafeAttachment[] (cho A).

    Hành vi lỗi:
        Mọi lỗi nội bộ được log và pipeline trả ProcessedEmail hợp lệ
        (có thể có label=OTHER, safety=SUSPICIOUS) thay vì crash.
    """
    cfg = settings or get_settings()

    # --- 0. Đọc file nếu cần ---
    if isinstance(raw, Path):
        try:
            raw_bytes = raw.read_bytes()
        except OSError as exc:
            logger.error("Không đọc được file .eml '%s': %s", raw, exc)
            raw_bytes = b""
    else:
        raw_bytes = raw

    # --- 1. Parse ---
    parsed, saved_attachments = parse_eml(
        raw_bytes,
        attachments_dir=cfg.attachments_dir,
        max_attach_bytes=cfg.attach_max_bytes,
        save_attachments=bool(raw_bytes),  # không lưu khi bytes rỗng
    )

    # --- 3. Quét offline (stub WP-00) ---
    url_findings, sender_reasons = _stub_scan_urls(
        parsed.urls, parsed.html_links, parsed.sender, cfg
    )
    attach_findings = _stub_scan_attachments(saved_attachments, cfg)

    # --- 5. Tổng hợp safety trước phân loại ---
    url_statuses = [f.status for f in url_findings]
    attach_statuses = [f.status for f in attach_findings]
    # sender_reasons có thể mang status riêng (stub: không có)
    safety_pre = aggregate_safety(*url_statuses, *attach_statuses)

    # --- 6. Phân loại ---
    # Plan § 4: nếu MALICIOUS → chỉ dùng TF-IDF cục bộ, không gọi LLM.
    # Ở WP-00 cả hai đều là stub nên không có sự khác biệt.
    label, confidence = _stub_classify(parsed)
    classifier_method = "stub"

    # --- 7. Tổng hợp safety cuối (áp dụng quy tắc nhãn) ---
    safety_final = aggregate_safety(
        *url_statuses,
        *attach_statuses,
        label_is_phishing=(label is EmailLabel.PHISHING),
    )

    # --- 8. Tóm tắt (stub: None) ---
    summary: str | None = None

    # --- 9. Dựng ClassifiedEmail ---
    # received_at phải là datetime; parser đảm bảo điều này
    received_at = parsed.received_at
    if hasattr(received_at, "tzinfo") and received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=timezone.utc)

    # Danh sách đường dẫn file đính kèm đã lưu (chỉ dùng trong ClassifiedEmail.attachments)
    attachment_paths = [sa.path for sa in saved_attachments if sa.path]

    classified = ClassifiedEmail(
        id=parsed.message_id,
        sender=parsed.sender,
        subject=parsed.subject,
        body=parsed.body_text,
        received_at=received_at,
        label=label,
        safety=safety_final,
        summary=summary,
        attachments=attachment_paths,
        label_confidence=confidence,
    )

    # --- 9b. Dựng SafeAttachment chỉ cho file SAFE ---
    safe_attachments: list[SafeAttachment] = []
    for finding in attach_findings:
        if finding.status is SafetyStatus.SAFE and finding.path and finding.sha256:
            try:
                sa = SafeAttachment(
                    path=finding.path,
                    sha256=finding.sha256,
                    email_id=parsed.message_id,
                )
                safe_attachments.append(sa)
            except ValueError as exc:
                logger.error("Không tạo SafeAttachment cho '%s': %s", finding.filename, exc)

    # --- 10. Quyết định chuyển tiếp ---
    forward = can_forward_email(classified, user_approved=False)

    return ProcessedEmail(
        email=classified,
        safe_attachments=safe_attachments,
        url_findings=url_findings,
        attachment_findings=attach_findings,
        sender_reasons=sender_reasons,
        classifier_method=classifier_method,
        can_forward=forward,
        user_approved=False,
    )


def approve_suspicious(processed: ProcessedEmail) -> ProcessedEmail:
    """Người dùng xác nhận muốn chuyển tiếp email SUSPICIOUS.

    Tạo SafeAttachment cho các file có status SUSPICIOUS (nếu chưa tạo).
    Đánh dấu user_approved=True và cập nhật can_forward.

    Email MALICIOUS: hàm này KHÔNG thay đổi kết quả (can_forward vẫn False).
    """
    if processed.email.safety is SafetyStatus.MALICIOUS:
        logger.warning(
            "approve_suspicious() bị bỏ qua: email '%s' là MALICIOUS",
            processed.email.id,
        )
        return processed

    # Tạo thêm SafeAttachment cho file SUSPICIOUS (nếu chưa có)
    existing_paths = {sa.path for sa in processed.safe_attachments}
    extra: list[SafeAttachment] = []
    for finding in processed.attachment_findings:
        if finding.status is SafetyStatus.SUSPICIOUS and finding.path not in existing_paths:
            if finding.path and finding.sha256:
                try:
                    extra.append(SafeAttachment(
                        path=finding.path,
                        sha256=finding.sha256,
                        email_id=processed.email.id,
                    ))
                except ValueError as exc:
                    logger.error("approve_suspicious: không tạo SafeAttachment: %s", exc)

    new_forward = can_forward_email(processed.email, user_approved=True)

    return ProcessedEmail(
        email=processed.email,
        safe_attachments=processed.safe_attachments + extra,
        url_findings=processed.url_findings,
        attachment_findings=processed.attachment_findings,
        sender_reasons=processed.sender_reasons,
        classifier_method=processed.classifier_method,
        can_forward=new_forward,
        user_approved=True,
    )


def process_many(
    raws: list[bytes | Path],
    *,
    settings: Settings | None = None,
) -> list[ProcessedEmail]:
    """Xử lý nhiều email, bỏ qua lỗi đơn lẻ."""
    cfg = settings or get_settings()
    results: list[ProcessedEmail] = []
    for raw in raws:
        try:
            results.append(process_email(raw, settings=cfg))
        except Exception as exc:  # noqa: BLE001
            logger.error("Lỗi xử lý email: %s", exc)
    return results
