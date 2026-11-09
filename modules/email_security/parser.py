"""Parse file .eml thành ParsedEmail (WP-01, plan_module_d.md § WP-01).

Chỉ dùng thư viện stdlib: email, html.parser, hashlib, pathlib, uuid, logging.
Không import streamlit hay scikit-learn — module này phải testable offline hoàn toàn.

Luồng chính:
    raw_bytes → email.message_from_bytes(policy=default)
              → trích header (Message-ID, From, Subject, Date, Reply-To, Authentication-Results)
              → walk parts → body_text (plain ưu tiên, html fallback)
              → html_links (nếu có HTML)
              → raw_attachments (tên + bytes)
              → ParsedEmail
"""
from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from email import message_from_bytes, policy as email_policy
from email.headerregistry import Address
from email.message import EmailMessage
from html.parser import HTMLParser
from pathlib import Path
from typing import NamedTuple

from .models import ParsedEmail
from .urls import extract_html_links, extract_urls

logger = logging.getLogger(__name__)

# Ký tự không hợp lệ trong tên file trên mọi hệ điều hành
_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MAX_FILENAME_LEN = 100


# ---------------------------------------------------------------------------
# Tiện ích nội bộ
# ---------------------------------------------------------------------------

class _TextHTMLExtractor(HTMLParser):
    """Lấy văn bản thuần từ HTML, bỏ script/style."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip: int = 0  # độ sâu trong thẻ bị bỏ qua

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(" ".join(self._parts).split())


def _strip_html(html: str) -> str:
    """Chuyển HTML thành văn bản thuần, bỏ script/style."""
    try:
        extractor = _TextHTMLExtractor()
        extractor.feed(html)
        return extractor.get_text()
    except Exception:
        return re.sub(r"<[^>]+>", " ", html)


def _decode_part(part: EmailMessage) -> str:
    """Giải mã một phần email thành chuỗi, dùng errors='replace' khi lỗi charset."""
    try:
        payload = part.get_payload(decode=True)
        if payload is None:
            return ""
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except (LookupError, UnicodeDecodeError):
            # Thử chardet nếu có
            try:
                import chardet  # noqa: PLC0415
                detected = chardet.detect(payload)
                enc = detected.get("encoding") or "utf-8"
                return payload.decode(enc, errors="replace")
            except ImportError:
                return payload.decode("utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Không giải mã được phần email: %s", exc)
        return ""


def _sanitize_filename(raw: str) -> str:
    """Làm sạch tên file đính kèm:
    - Bỏ ký tự điều khiển và ký tự đặc biệt nguy hiểm.
    - Bỏ path component (chỉ giữ basename).
    - Giới hạn 100 ký tự.
    - Bỏ leading dots để tránh file ẩn.
    """
    # Lấy basename (chống path traversal: ../../evil.exe)
    name = Path(raw).name
    # Bỏ ký tự điều khiển Unicode
    name = "".join(ch for ch in name if unicodedata.category(ch) != "Cc")
    # Thay ký tự không an toàn bằng dấu gạch dưới
    name = _UNSAFE_FILENAME_CHARS.sub("_", name)
    # Bỏ leading dots/spaces
    name = name.lstrip(". ")
    # Giới hạn độ dài
    if len(name) > _MAX_FILENAME_LEN:
        stem = Path(name).stem[:_MAX_FILENAME_LEN - 10]
        suffix = Path(name).suffix[:10]
        name = stem + suffix
    return name or "attachment"


def _sha256_bytes(data: bytes) -> str:
    """Tính SHA-256 của dữ liệu bytes, trả 64 ký tự hex lowercase."""
    return hashlib.sha256(data).hexdigest()


def _parse_sender(msg: EmailMessage) -> str:
    """Trích địa chỉ email người gửi từ header From.

    Trả chuỗi 'name <addr>' hoặc chỉ 'addr'. Không bao giờ trả chuỗi rỗng
    (fallback: 'unknown@unknown').
    """
    from_header = msg.get("From", "")
    try:
        # email.policy.default parse From thành list[Address]
        addresses = msg["From"].addresses  # type: ignore[union-attr]
        if addresses:
            addr: Address = addresses[0]
            if addr.display_name:
                return f"{addr.display_name} <{addr.addr_spec}>"
            return addr.addr_spec
    except Exception:
        pass
    # Fallback: dùng header thô
    return from_header.strip() or "unknown@unknown"


def _parse_reply_to(msg: EmailMessage) -> str | None:
    raw = msg.get("Reply-To", "").strip()
    return raw or None


def _parse_date(msg: EmailMessage) -> datetime:
    """Parse header Date thành datetime UTC. Fallback: now(UTC) + log WARNING."""
    try:
        date_obj = msg["Date"].datetime  # type: ignore[union-attr]
        if date_obj is not None:
            if date_obj.tzinfo is None:
                date_obj = date_obj.replace(tzinfo=timezone.utc)
            return date_obj
    except Exception:
        pass
    logger.warning("Header Date thiếu hoặc sai định dạng — dùng thời điểm hiện tại (UTC)")
    return datetime.now(timezone.utc)


def _parse_message_id(msg: EmailMessage) -> str:
    """Lấy Message-ID, slug hoá để dùng làm tên thư mục an toàn.

    Nếu thiếu → sinh UUID4 và log WARNING.
    """
    raw = msg.get("Message-ID", "").strip()
    if not raw:
        generated = str(uuid.uuid4())
        logger.warning("Thiếu header Message-ID — sinh UUID: %s", generated)
        return generated
    # Bỏ < > bao quanh
    cleaned = raw.strip("<>").strip()
    # Slug hoá: chỉ giữ ký tự an toàn cho tên thư mục
    slug = re.sub(r"[^a-zA-Z0-9._@-]", "_", cleaned)
    return slug[:200] or str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Hàm công khai
# ---------------------------------------------------------------------------

class SavedAttachment(NamedTuple):
    """Thông tin file đính kèm đã lưu xuống disk."""
    filename: str    # tên đã làm sạch
    path: str        # đường dẫn tương đối
    sha256: str      # 64 ký tự hex lowercase
    size: int        # kích thước byte
    mimetype: str    # MIME type khai báo trong email


def save_attachment(
    filename_raw: str,
    content: bytes,
    email_slug: str,
    attachments_dir: str = "data/real",
) -> SavedAttachment:
    """Lưu bytes file đính kèm vào disk và trả metadata.

    Tên file lưu theo mẫu: ``<sha256[:16]>_<tên đã làm sạch>``
    để tránh đụng độ và path traversal (plan A9).

    Args:
        filename_raw: Tên file gốc từ email (chưa làm sạch).
        content: Bytes nội dung file.
        email_slug: Tên slug của email (dùng làm thư mục con).
        attachments_dir: Thư mục gốc lưu file đính kèm.

    Returns:
        SavedAttachment với đường dẫn tương đối và SHA-256.
    """
    clean_name = _sanitize_filename(filename_raw)
    sha = _sha256_bytes(content)
    safe_name = f"{sha[:16]}_{clean_name}"

    dest_dir = Path(attachments_dir) / email_slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / safe_name
    dest_path.write_bytes(content)

    # Đường dẫn tương đối (relative to repo root)
    try:
        rel_path = str(dest_path.relative_to(Path.cwd()))
    except ValueError:
        rel_path = str(dest_path)

    return SavedAttachment(
        filename=clean_name,
        path=rel_path.replace("\\", "/"),
        sha256=sha,
        size=len(content),
        mimetype="application/octet-stream",  # sẽ được cập nhật bởi caller
    )


def parse_eml(
    raw_content: bytes,
    *,
    attachments_dir: str = "data/real",
    max_attach_bytes: int = 50 * 1024 * 1024,
    save_attachments: bool = True,
) -> tuple[ParsedEmail, list[SavedAttachment]]:
    """Parse file .eml thành ParsedEmail + danh sách file đính kèm đã lưu.

    Args:
        raw_content: Nội dung file .eml dưới dạng bytes.
        attachments_dir: Thư mục lưu file đính kèm (data/real/).
        max_attach_bytes: Giới hạn kích thước một file đính kèm.
            File vượt ngưỡng → được ghi nhận trong raw_attachments nhưng
            không lưu (content=b'' + oversized=True).
        save_attachments: False → không lưu file (dùng trong test).

    Returns:
        Tuple (ParsedEmail, list[SavedAttachment]).
        SavedAttachment.path rỗng nếu save_attachments=False hoặc file quá lớn.

    Raises:
        Không raise exception — mọi lỗi parse được log và trả giá trị mặc định.
    """
    try:
        msg: EmailMessage = message_from_bytes(
            raw_content,
            policy=email_policy.default,
        )  # type: ignore[arg-type]
    except Exception as exc:
        logger.error("Lỗi parse email: %s", exc)
        # Trả ParsedEmail trống để pipeline không crash
        return _empty_parsed_email(), []

    message_id = _parse_message_id(msg)
    sender = _parse_sender(msg)
    subject = msg.get("Subject", "").strip() or "(không có tiêu đề)"
    received_at = _parse_date(msg)
    reply_to = _parse_reply_to(msg)
    auth_results = msg.get("Authentication-Results", "").strip() or None

    # --- Thu thập body ---
    body_plain: list[str] = []
    body_html: list[str] = []
    raw_attachments_meta: list[dict] = []
    saved: list[SavedAttachment] = []

    for part in msg.walk():
        content_type = part.get_content_type()
        content_disp = str(part.get_content_disposition() or "")

        # Bỏ qua container multipart
        if content_type.startswith("multipart/"):
            continue

        # File đính kèm
        if "attachment" in content_disp or part.get_filename():
            fname_raw = part.get_filename() or "attachment"
            payload: bytes = part.get_payload(decode=True) or b""
            oversized = len(payload) > max_attach_bytes
            if oversized:
                logger.warning(
                    "File đính kèm '%s' vượt giới hạn %d MB — bỏ qua nội dung",
                    fname_raw,
                    max_attach_bytes // (1024 * 1024),
                )
            raw_attachments_meta.append({
                "filename": fname_raw,
                "content": b"" if oversized else payload,
                "mimetype": content_type,
                "oversized": oversized,
            })
            if save_attachments and not oversized and payload:
                sa = save_attachment(
                    fname_raw, payload, message_id, attachments_dir
                )
                saved.append(SavedAttachment(
                    filename=sa.filename,
                    path=sa.path,
                    sha256=sa.sha256,
                    size=sa.size,
                    mimetype=content_type,
                ))
            continue

        # Body
        if content_type == "text/plain":
            body_plain.append(_decode_part(part))  # type: ignore[arg-type]
        elif content_type == "text/html":
            body_html.append(_decode_part(part))  # type: ignore[arg-type]

    # --- Chọn body ---
    if body_plain:
        body_text = "\n".join(body_plain).strip()
        html_links: list[tuple[str, str]] = []
    elif body_html:
        combined_html = "\n".join(body_html)
        body_text = _strip_html(combined_html).strip()
        html_links = extract_html_links(combined_html)
    else:
        body_text = ""
        html_links = []

    # --- Trích URL ---
    urls = extract_urls(body_text, html_links)

    parsed = ParsedEmail(
        message_id=message_id,
        sender=sender,
        subject=subject,
        received_at=received_at,
        body_text=body_text,
        urls=urls,
        html_links=html_links,
        reply_to=reply_to,
        auth_results=auth_results,
        raw_attachments=raw_attachments_meta,
    )
    return parsed, saved


def _empty_parsed_email() -> ParsedEmail:
    """ParsedEmail rỗng — dùng khi parse thất bại hoàn toàn."""
    return ParsedEmail(
        message_id=str(uuid.uuid4()),
        sender="unknown@unknown",
        subject="(lỗi parse)",
        received_at=datetime.now(timezone.utc),
        body_text="",
        urls=[],
        html_links=[],
        reply_to=None,
        auth_results=None,
        raw_attachments=[],
    )
