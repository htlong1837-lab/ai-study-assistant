"""Luồng xử lý email thật cho Module D, với cổng chặn fail-closed."""

from __future__ import annotations

import logging
import os
from datetime import timezone
from pathlib import Path

from core.contracts import ClassifiedEmail, EmailLabel, SafeAttachment, SafetyStatus

from .attachment_scanner import scan_attachment
from .classifier import BaselineClassifier, LLMZeroShotClassifier
from .config import Settings, get_settings
from .models import AttachmentFinding, ParsedEmail, ProcessedEmail, Reason
from .parser import SavedAttachment, parse_eml
from .redact import redact_pii
from .safety import aggregate_safety, can_forward_email, max_status
from .summarizer import summarize_email
from .url_scanner import scan_url, scan_urls
from .urls import normalize_url
from .virustotal import VirusTotalClient, verify_attachment_with_vt, verify_url_with_vt

logger = logging.getLogger(__name__)
_CLASSIFIER: BaselineClassifier | None = None


def _get_baseline() -> BaselineClassifier:
    global _CLASSIFIER
    if _CLASSIFIER is None:
        data_path = Path("data/emails_labeled.jsonl")
        model_path = Path("data/models/email_classifier.joblib")
        _CLASSIFIER = BaselineClassifier.load_or_train(model_path, data_path)
    return _CLASSIFIER


def _classify(
    parsed: ParsedEmail, *, allow_llm: bool, settings: Settings
) -> tuple[EmailLabel, float, str]:
    """Dùng TF-IDF mặc định; chỉ chuyển sang zero-shot khi được cấu hình."""
    text = f"{parsed.subject}\n{parsed.body_text}".strip()
    mode = os.getenv("EMAIL_CLASSIFIER", "tfidf").strip().lower()
    if mode in {"llm", "zero-shot", "zeroshot"} and allow_llm:
        label, confidence = LLMZeroShotClassifier().predict(redact_pii(text))
        if confidence > 0.0 or label is not EmailLabel.OTHER:
            return label, confidence, "llm"
        try:
            label, confidence = _get_baseline().predict(text)
            return label, confidence, "fallback"
        except Exception:
            return EmailLabel.OTHER, 0.0, "fallback"
    try:
        label, confidence = _get_baseline().predict(text)
        return label, confidence, "tfidf"
    except Exception as exc:  # dataset/model lỗi vẫn trả contract hợp lệ
        logger.warning("TF-IDF classifier unavailable; using OTHER: %s", exc)
        return EmailLabel.OTHER, 0.0, "fallback"


def _scan_urls(parsed: ParsedEmail, settings: Settings, vt: VirusTotalClient | None):
    normalized = list(
        dict.fromkeys(u for raw in parsed.urls if (u := normalize_url(raw)))
    )
    findings = scan_urls(normalized)
    if vt:
        for finding in findings:
            if finding.status is SafetyStatus.SUSPICIOUS:
                old_status = finding.status
                verify_url_with_vt(finding, client=vt)
                # Ngưỡng cấu hình VT, đồng thời không để verdict sạch xóa heuristic.
                rep = finding.reputation
                vt_status = SafetyStatus.SAFE
                if rep and rep.malicious >= settings.vt_malicious_threshold:
                    vt_status = SafetyStatus.MALICIOUS
                elif rep and (
                    rep.malicious > 0
                    or rep.suspicious >= settings.vt_suspicious_threshold
                ):
                    vt_status = SafetyStatus.SUSPICIOUS
                finding.status = max_status(old_status, vt_status)

    sender_reasons: list[Reason] = []
    sender = scan_url(parsed.sender) if "://" in parsed.sender else None
    if sender:
        sender_reasons.extend(sender.reasons)
    if parsed.reply_to and parsed.sender:
        from_domain = parsed.sender.rsplit("@", 1)[-1].lower().strip(" >")
        reply_domain = parsed.reply_to.rsplit("@", 1)[-1].lower().strip(" >")
        if from_domain and reply_domain and from_domain != reply_domain:
            sender_reasons.append(
                Reason("REPLY_TO_MISMATCH", "Reply-To khác tên miền người gửi.")
            )
    auth = (parsed.auth_results or "").lower()
    if any(signal in auth for signal in ("spf=fail", "dkim=fail", "dmarc=fail")):
        sender_reasons.append(
            Reason(
                "AUTHENTICATION_FAILED", "Email không vượt qua kiểm tra SPF/DKIM/DMARC."
            )
        )
    return findings, sender_reasons


def _scan_attachments(
    parsed: ParsedEmail,
    saved: list[SavedAttachment],
    settings: Settings,
    vt: VirusTotalClient | None,
) -> list[AttachmentFinding]:
    by_name = {item.filename: item for item in saved}
    results: list[AttachmentFinding] = []
    for item in parsed.raw_attachments:
        filename = str(item.get("filename") or "attachment")
        content = item.get("content") or b""
        saved_item = by_name.get(filename)
        path = saved_item.path if saved_item else ""
        if item.get("oversized"):
            results.append(
                AttachmentFinding(
                    filename,
                    path,
                    "",
                    0,
                    SafetyStatus.SUSPICIOUS,
                    [
                        Reason(
                            "SIZE_EXCEEDED",
                            "Tệp vượt giới hạn kích thước nên chưa quét đầy đủ.",
                        )
                    ],
                )
            )
            continue
        result = scan_attachment(
            content,
            filename,
            path,
            parsed.message_id,
            max_bytes=settings.attach_max_bytes,
        )
        finding = result.to_finding()
        finding.size = len(content)
        if vt and finding.status is SafetyStatus.SUSPICIOUS:
            old_status = finding.status
            verify_attachment_with_vt(finding, client=vt, email_id=parsed.message_id)
            rep = finding.reputation
            vt_status = SafetyStatus.SAFE
            if rep and rep.malicious >= settings.vt_malicious_threshold:
                vt_status = SafetyStatus.MALICIOUS
            elif rep and (
                rep.malicious > 0 or rep.suspicious >= settings.vt_suspicious_threshold
            ):
                vt_status = SafetyStatus.SUSPICIOUS
            finding.status = max_status(old_status, vt_status)
        results.append(finding)
    return results


def process_email(
    raw: bytes | Path, *, settings: Settings | None = None
) -> ProcessedEmail:
    """Parse, quét, phân loại và dựng kết quả chỉ chuyển tiếp khi qua cổng."""
    cfg = settings or get_settings()
    try:
        raw_bytes = raw.read_bytes() if isinstance(raw, Path) else raw
    except OSError as exc:
        logger.error("Không đọc được file .eml '%s': %s", raw, exc)
        raw_bytes = b""

    parsed, saved = parse_eml(
        raw_bytes,
        attachments_dir=cfg.attachments_dir,
        max_attach_bytes=cfg.attach_max_bytes,
        save_attachments=bool(raw_bytes),
    )
    vt = (
        VirusTotalClient(api_key=cfg.virustotal_api_key) if cfg.has_virustotal else None
    )
    url_findings, sender_reasons = _scan_urls(parsed, cfg, vt)
    attachment_findings = _scan_attachments(parsed, saved, cfg, vt)
    pre_statuses = [f.status for f in url_findings] + [
        f.status for f in attachment_findings
    ]
    if sender_reasons:
        pre_statuses.append(SafetyStatus.SUSPICIOUS)
    safety_pre = aggregate_safety(*pre_statuses)

    label, confidence, method = _classify(
        parsed, allow_llm=safety_pre is not SafetyStatus.MALICIOUS, settings=cfg
    )
    safety = aggregate_safety(
        *pre_statuses, label_is_phishing=label is EmailLabel.PHISHING
    )

    summary = None
    if safety is SafetyStatus.SAFE and label in {
        EmailLabel.ASSIGNMENT,
        EmailLabel.ANNOUNCEMENT,
        EmailLabel.SCHEDULE,
    }:
        summary = summarize_email(
            parsed.subject,
            parsed.body_text,
            label,
            safety,
        )

    received_at = parsed.received_at
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=timezone.utc)
    classified = ClassifiedEmail(
        id=parsed.message_id,
        sender=parsed.sender,
        subject=parsed.subject,
        body=parsed.body_text,
        received_at=received_at,
        label=label,
        safety=safety,
        summary=summary,
        attachments=[a.path for a in saved if a.path],
        label_confidence=confidence,
    )
    safe_attachments = []
    if safety is not SafetyStatus.MALICIOUS:
        for finding in attachment_findings:
            if finding.status is SafetyStatus.SAFE and finding.path and finding.sha256:
                try:
                    safe_attachments.append(
                        SafeAttachment(finding.path, finding.sha256, parsed.message_id)
                    )
                except ValueError as exc:
                    logger.error(
                        "Không thể tạo SafeAttachment cho %s: %s", finding.filename, exc
                    )
    return ProcessedEmail(
        email=classified,
        safe_attachments=safe_attachments,
        url_findings=url_findings,
        attachment_findings=attachment_findings,
        sender_reasons=sender_reasons,
        classifier_method=method,
        can_forward=can_forward_email(classified),
        user_approved=False,
    )


def approve_suspicious(processed: ProcessedEmail) -> ProcessedEmail:
    """Duyệt email nghi ngờ; MALICIOUS tuyệt đối không thể được duyệt."""
    if processed.email.safety is SafetyStatus.MALICIOUS:
        return processed
    extra = []
    existing = {attachment.path for attachment in processed.safe_attachments}
    for finding in processed.attachment_findings:
        if (
            finding.status is SafetyStatus.SUSPICIOUS
            and finding.path
            and finding.sha256
            and finding.path not in existing
        ):
            extra.append(
                SafeAttachment(finding.path, finding.sha256, processed.email.id)
            )
    return ProcessedEmail(
        email=processed.email,
        safe_attachments=processed.safe_attachments + extra,
        url_findings=processed.url_findings,
        attachment_findings=processed.attachment_findings,
        sender_reasons=processed.sender_reasons,
        classifier_method=processed.classifier_method,
        can_forward=can_forward_email(processed.email, user_approved=True),
        user_approved=True,
    )


def process_many(
    raws: list[bytes | Path], *, settings: Settings | None = None
) -> list[ProcessedEmail]:
    cfg = settings or get_settings()
    results = []
    for raw in raws:
        try:
            results.append(process_email(raw, settings=cfg))
        except Exception as exc:  # noqa: BLE001
            logger.error("Lỗi xử lý email: %s", exc)
    return results
