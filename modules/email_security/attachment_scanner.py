"""WP-08 — Quét an toàn file đính kèm (Heuristic + Magic Bytes).

Luồng kiểm tra (theo plan_module_d.md § 6.3):
  1. Kiểm tra kích thước → SUSPICIOUS (không lưu, không kiểm tra tiếp)
  2. Kiểm tra đuôi kép / đuôi cuối ∈ denylist cứng → MALICIOUS
  3. Kiểm tra magic bytes (PE, ELF, Mach-O) → MALICIOUS
  4. Kiểm tra header PDF mismatch → SUSPICIOUS
  5. Kiểm tra nội dung ZIP (file nguy hiểm bên trong / mật khẩu) → MALICIOUS / SUSPICIOUS
  6. Đuôi macro / nén / HTML → SUSPICIOUS
  7. Còn lại → SAFE

Quy tắc "Chặn tại cổng":
  - Chỉ tạo SafeAttachment khi status == SAFE.
  - Khi allow_suspicious=True, cũng tạo SafeAttachment cho SUSPICIOUS.
  - Tuyệt đối không tạo SafeAttachment cho MALICIOUS.
"""

from __future__ import annotations

import hashlib
import io
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from core.contracts import SafeAttachment, SafetyStatus

from .models import AttachmentFinding, Reason, Reputation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Danh sách phân loại đuôi file
# ---------------------------------------------------------------------------

#: Denylist cứng — chặn ngay, không cần VT (plan § 6.3 + yêu cầu đề bài)
DANGEROUS_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".exe", ".bat", ".cmd", ".com", ".scr", ".pif",
        ".vbs", ".vbe", ".js",  ".jse", ".wsf", ".wsh",
        ".ps1", ".msi", ".msp", ".hta", ".cpl", ".jar",
        ".reg", ".lnk", ".dll", ".sys",
        # thêm từ plan: iso img
        ".iso", ".img",
    }
)

#: Đuôi gây SUSPICIOUS (macro, nén, HTML) — plan § 6.3
SUSPICIOUS_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".docm", ".xlsm", ".pptm",
        ".zip",  ".rar",  ".7z",
        ".html", ".htm",
    }
)

#: Đuôi hợp lệ, rủi ro thấp — plan § 6.3 (VT 404 → SAFE)
LOW_RISK_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pdf",  ".docx", ".xlsx", ".pptx",
        ".txt",  ".csv",
        ".png",  ".jpg",  ".jpeg",
    }
)

# ---------------------------------------------------------------------------
# Magic bytes
# ---------------------------------------------------------------------------

MAGIC_PE     = b"\x4d\x5a"           # MZ — Windows PE executable
MAGIC_ELF    = b"\x7fELF"            # ELF — Linux/Unix executable
MAGIC_MACHO1 = b"\xcf\xfa\xed\xfe"   # Mach-O little-endian
MAGIC_MACHO2 = b"\xfe\xed\xfa\xcf"   # Mach-O big-endian

EXECUTABLE_MAGICS: tuple[bytes, ...] = (MAGIC_PE, MAGIC_ELF, MAGIC_MACHO1, MAGIC_MACHO2)

MAGIC_PDF = b"%PDF-"  # 5 byte đầu của PDF hợp lệ

#: Đuôi tài liệu/hình ảnh KHÔNG được có magic bytes thực thi
DOCUMENT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pdf",  ".docx", ".xlsx", ".pptx",
        ".txt",  ".jpg",  ".jpeg", ".png",
    }
)


# ---------------------------------------------------------------------------
# Dataclass kết quả
# ---------------------------------------------------------------------------


@dataclass
class AttachmentScanResult:
    """Kết quả quét một file đính kèm.

    ``safe_attachment`` chỉ khác None khi status SAFE (hoặc SUSPICIOUS + allow_suspicious=True).
    Luôn trả về None nếu MALICIOUS — đây là quy tắc "Chặn tại cổng".
    """

    filename: str
    file_path: str
    sha256: str
    status: SafetyStatus
    reasons: list[str] = field(default_factory=list)
    safe_attachment: SafeAttachment | None = None
    reputation: Reputation | None = None

    def to_finding(self) -> AttachmentFinding:
        """Chuyển sang AttachmentFinding (models.py) để ghi vào ProcessedEmail."""
        reason_objs = [
            Reason(code=_reason_code(r), message=r) for r in self.reasons
        ]
        return AttachmentFinding(
            filename=self.filename,
            path=self.file_path,
            sha256=self.sha256,
            size=0,  # kích thước được ghi ở pipeline khi có dữ liệu gốc
            status=self.status,
            reasons=reason_objs,
            reputation=self.reputation,
        )


# ---------------------------------------------------------------------------
# Hàm tiện ích nội bộ
# ---------------------------------------------------------------------------


def _sha256_hex(data: bytes) -> str:
    """Tính SHA-256 → 64 ký tự hex chữ thường (đã đúng định dạng SafeAttachment)."""
    return hashlib.sha256(data).hexdigest()


def _all_suffixes(filename: str) -> list[str]:
    """Trả về tất cả đuôi file (chữ thường), ví dụ 'baitap.pdf.exe' → ['.pdf', '.exe']."""
    return [s.lower() for s in Path(filename).suffixes]


def _final_suffix(filename: str) -> str:
    """Trả về đuôi cuối (chữ thường), ví dụ 'report.PDF' → '.pdf'."""
    return Path(filename).suffix.lower()


def _reason_code(message: str) -> str:
    """Suy ra mã lý do ngắn gọn từ nội dung thông báo (dùng cho Reason.code)."""
    msg = message.upper()
    if "KÍCH THƯỚC" in msg or "VƯỢT GIỚI HẠN" in msg:
        return "SIZE_EXCEEDED"
    if "NGUY HIỂM" in msg or "MỞ RỘNG" in msg:
        return "DANGEROUS_EXT"
    if "MZ" in msg or "ELF" in msg or "MACH" in msg or "MAGIC" in msg or "THỰC THI" in msg:
        return "MAGIC_MISMATCH"
    if "GIẢ DANH" in msg or "GIẢ MẠO" in msg:
        return "MAGIC_SPOOF"
    if "HEADER" in msg or "%PDF" in msg or "PDF" in msg:
        return "INVALID_HEADER"
    if "MẬT KHẨU" in msg:
        return "ZIP_ENCRYPTED"
    if "ZIP" in msg and "NGUY HIỂM" in msg.replace("KÍCH THƯỚC", ""):
        return "ZIP_MALICIOUS_ENTRY"
    if "ZIP" in msg:
        return "ZIP_SUSPICIOUS"
    if "MACRO" in msg:
        return "MACRO_EXT"
    if "NÉN" in msg or "HTML" in msg:
        return "SUSPICIOUS_EXT"
    return "HEURISTIC"


def _has_executable_magic(data: bytes) -> bool:
    """Kiểm tra 4–8 byte đầu có phải magic bytes của file thực thi không."""
    for magic in EXECUTABLE_MAGICS:
        if data[: len(magic)] == magic:
            return True
    return False


def _check_zip_contents(
    data: bytes,
    filename: str,
) -> tuple[SafetyStatus, list[str]]:
    """Kiểm tra nội dung file ZIP.

    Returns:
        (status, reasons) — chỉ MALICIOUS hoặc SUSPICIOUS; SAFE nếu không có vấn đề.
    """
    reasons: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            # Kiểm tra file có mật khẩu (flag_bits bit 0)
            if any(info.flag_bits & 0x1 for info in zf.infolist()):
                reasons.append(
                    "File ZIP được bảo vệ bằng mật khẩu — không thể kiểm tra nội dung."
                )
                return SafetyStatus.SUSPICIOUS, reasons

            # Kiểm tra từng entry
            for name in zf.namelist():
                entry_ext = Path(name).suffix.lower()
                if entry_ext in DANGEROUS_EXTENSIONS:
                    reasons.append(
                        f"File ZIP chứa tệp thực thi nguy hiểm bên trong: '{name}'."
                    )
                    return SafetyStatus.MALICIOUS, reasons
    except zipfile.BadZipFile:
        reasons.append("File .zip không hợp lệ hoặc bị hỏng — có thể bị giả mạo.")
        return SafetyStatus.SUSPICIOUS, reasons

    return SafetyStatus.SAFE, reasons


# ---------------------------------------------------------------------------
# Hàm quét chính
# ---------------------------------------------------------------------------


def scan_attachment(
    data: bytes,
    filename: str,
    file_path: str,
    email_id: str,
    max_bytes: int = 50 * 1024 * 1024,
    allow_suspicious: bool = False,
) -> AttachmentScanResult:
    """Quét an toàn một file đính kèm (100% offline).

    Args:
        data:             Nội dung file (bytes đã giải mã từ email).
        filename:         Tên file đã làm sạch (không có đường dẫn).
        file_path:        Đường dẫn tương đối sau khi lưu (ghi vào SafeAttachment.path).
        email_id:         ID email chứa file này (ghi vào SafeAttachment.email_id).
        max_bytes:        Ngưỡng kích thước tối đa (byte). Mặc định 50 MB.
        allow_suspicious: Nếu True, tạo SafeAttachment ngay cả khi SUSPICIOUS.

    Returns:
        AttachmentScanResult với status, reasons và safe_attachment (nếu được phép).
    """
    sha = _sha256_hex(data)
    reasons: list[str] = []

    # ------------------------------------------------------------------
    # Bước 1 — Kiểm tra kích thước
    # ------------------------------------------------------------------
    if len(data) > max_bytes:
        msg = (
            f"File vượt giới hạn kích thước ({len(data):,} byte > "
            f"{max_bytes:,} byte). Không lưu để kiểm tra thêm."
        )
        reasons.append(msg)
        logger.warning("[attachment_scanner] SIZE_EXCEEDED: %s — %s", filename, msg)
        return _make_result(
            filename, file_path, sha, SafetyStatus.SUSPICIOUS,
            reasons, email_id, allow_suspicious,
        )

    # ------------------------------------------------------------------
    # Bước 2 — Denylist đuôi (kể cả đuôi kép baitap.pdf.exe)
    # ------------------------------------------------------------------
    all_exts  = _all_suffixes(filename)
    final_ext = _final_suffix(filename)

    for ext in all_exts:
        if ext in DANGEROUS_EXTENSIONS:
            msg = f"Phần mở rộng nguy hiểm bị chặn: '{ext}' (file: '{filename}')."
            reasons.append(msg)
            logger.warning("[attachment_scanner] DANGEROUS_EXT: %s", msg)
            return _make_result(
                filename, file_path, sha, SafetyStatus.MALICIOUS,
                reasons, email_id, allow_suspicious,
            )

    # ------------------------------------------------------------------
    # Bước 3 — Magic bytes thực thi (PE/ELF/Mach-O)
    # ------------------------------------------------------------------
    header8 = data[:8]
    if _has_executable_magic(header8):
        if final_ext in DOCUMENT_EXTENSIONS:
            msg = (
                f"File '{filename}' mang magic bytes của file thực thi (PE/ELF/Mach-O) "
                "nhưng tên file giả dạng định dạng tài liệu — nghi ngờ giả mạo nguy hiểm."
            )
        else:
            msg = (
                f"File '{filename}' được phát hiện là file thực thi qua magic bytes "
                "(PE/ELF/Mach-O) — chặn ngay."
            )
        reasons.append(msg)
        logger.warning("[attachment_scanner] MAGIC_SPOOF/MALICIOUS: %s", msg)
        return _make_result(
            filename, file_path, sha, SafetyStatus.MALICIOUS,
            reasons, email_id, allow_suspicious,
        )

    # ------------------------------------------------------------------
    # Bước 4 — PDF header mismatch
    # ------------------------------------------------------------------
    status = SafetyStatus.SAFE

    if final_ext == ".pdf":
        pdf_header = data[:5]
        if len(data) < 5 or pdf_header != MAGIC_PDF:
            msg = (
                f"File '{filename}' có phần mở rộng .pdf nhưng 5 byte đầu "
                f"không phải '%PDF-' (thực tế: {pdf_header!r}). "
                "Có thể bị giả mạo hoặc bị hỏng."
            )
            reasons.append(msg)
            logger.warning("[attachment_scanner] INVALID_HEADER: %s", msg)
            status = SafetyStatus.SUSPICIOUS

    # ------------------------------------------------------------------
    # Bước 5 — Kiểm tra nội dung ZIP
    # ------------------------------------------------------------------
    if final_ext == ".zip" and status == SafetyStatus.SAFE:
        zip_status, zip_reasons = _check_zip_contents(data, filename)
        reasons.extend(zip_reasons)
        if zip_status == SafetyStatus.MALICIOUS:
            return _make_result(
                filename, file_path, sha, SafetyStatus.MALICIOUS,
                reasons, email_id, allow_suspicious,
            )
        if zip_status == SafetyStatus.SUSPICIOUS:
            status = SafetyStatus.SUSPICIOUS

    # ------------------------------------------------------------------
    # Bước 6 — Đuôi macro / nén khác / HTML
    # ------------------------------------------------------------------
    if status == SafetyStatus.SAFE and final_ext in SUSPICIOUS_EXTENSIONS:
        # .zip đã xử lý ở bước 5 (nếu sạch thì vẫn SAFE)
        if final_ext != ".zip":
            if final_ext in {".docm", ".xlsm", ".pptm"}:
                msg = (
                    f"Định dạng '{final_ext}' hỗ trợ macro — có nguy cơ chứa "
                    "mã độc nhúng trong tài liệu."
                )
            elif final_ext in {".rar", ".7z"}:
                msg = (
                    f"Định dạng nén '{final_ext}' không thể kiểm tra nội dung bên trong "
                    "bằng thư viện chuẩn — đánh dấu nghi ngờ."
                )
            else:  # .html / .htm
                msg = (
                    f"Định dạng '{final_ext}' có thể chứa script độc hại nhúng "
                    "trong HTML."
                )
            reasons.append(msg)
            logger.info("[attachment_scanner] SUSPICIOUS_EXT: %s — %s", filename, msg)
            status = SafetyStatus.SUSPICIOUS

    # ------------------------------------------------------------------
    # Dựng kết quả cuối
    # ------------------------------------------------------------------
    return _make_result(
        filename, file_path, sha, status,
        reasons, email_id, allow_suspicious,
    )


# ---------------------------------------------------------------------------
# Hàm tạo kết quả (nội bộ)
# ---------------------------------------------------------------------------


def _make_result(
    filename: str,
    file_path: str,
    sha256: str,
    status: SafetyStatus,
    reasons: list[str],
    email_id: str,
    allow_suspicious: bool,
) -> AttachmentScanResult:
    """Tạo AttachmentScanResult và (nếu phù hợp) SafeAttachment."""
    safe_att: SafeAttachment | None = None

    should_create = status == SafetyStatus.SAFE or (
        status == SafetyStatus.SUSPICIOUS and allow_suspicious
    )
    # Quy tắc bất biến: MALICIOUS không bao giờ có SafeAttachment
    if status == SafetyStatus.MALICIOUS:
        should_create = False

    if should_create:
        try:
            safe_att = SafeAttachment(
                path=file_path,
                sha256=sha256,
                email_id=email_id,
            )
        except ValueError as exc:
            logger.error(
                "[attachment_scanner] Không thể tạo SafeAttachment cho '%s': %s",
                filename,
                exc,
            )

    return AttachmentScanResult(
        filename=filename,
        file_path=file_path,
        sha256=sha256,
        status=status,
        reasons=reasons,
        safe_attachment=safe_att,
    )
