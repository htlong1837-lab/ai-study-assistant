"""tests/email_security/test_attachment_scanner.py

Unit tests cho WP-08 — attachment_scanner.py.
Toàn bộ test chạy 100% offline (block_network fixture autouse từ conftest.py).
"""

from __future__ import annotations

import hashlib
import io
import zipfile

import pytest

from core.contracts import SafeAttachment, SafetyStatus
from modules.email_security.attachment_scanner import (
    DANGEROUS_EXTENSIONS,
    MAGIC_ELF,
    MAGIC_MACHO1,
    MAGIC_MACHO2,
    MAGIC_PDF,
    MAGIC_PE,
    SUSPICIOUS_EXTENSIONS,
    AttachmentScanResult,
    _sha256_hex,
    scan_attachment,
)

# ---------------------------------------------------------------------------
# Hằng số dùng chung
# ---------------------------------------------------------------------------

EMAIL_ID  = "test-email-001"
FILE_PATH = "data/real/test-email-001/file.pdf"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_zip(entries: dict[str, bytes], password: bytes | None = None) -> bytes:
    """Tạo bytes ZIP trong bộ nhớ.

    Args:
        entries:  dict tên_file → nội_dung.
        password: Nếu khác None, patch trực tiếp binary để set bit encryption (0x1)
                  trong cả local file header và central directory header,
                  vì zipfile stdlib không hỗ trợ ghi ZIP có mật khẩu.
    """
    import struct

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    zip_bytes = bytearray(buf.getvalue())

    if password:
        # Patch cả local file header (PK\x03\x04) và central dir (PK\x01\x02)
        i = 0
        while i < len(zip_bytes) - 4:
            sig = bytes(zip_bytes[i : i + 4])
            if sig == b"PK\x03\x04":
                flag_off = i + 6
                flags = struct.unpack_from("<H", zip_bytes, flag_off)[0]
                struct.pack_into("<H", zip_bytes, flag_off, flags | 0x1)
            elif sig == b"PK\x01\x02":
                flag_off = i + 8
                flags = struct.unpack_from("<H", zip_bytes, flag_off)[0]
                struct.pack_into("<H", zip_bytes, flag_off, flags | 0x1)
            i += 1

    return bytes(zip_bytes)


# ===========================================================================
# NHÓM 1 — Trường hợp SAFE
# ===========================================================================


class TestSafeFiles:
    """File sạch → SAFE + SafeAttachment được tạo."""

    def test_valid_pdf_safe(self) -> None:
        """PDF hợp lệ (đúng header %PDF-) → SAFE."""
        data = MAGIC_PDF + b"1.4 fake pdf content here"
        result = scan_attachment(data, "baocao.pdf", FILE_PATH, EMAIL_ID)

        assert result.status == SafetyStatus.SAFE
        assert result.reasons == []
        assert result.safe_attachment is not None
        assert isinstance(result.safe_attachment, SafeAttachment)

    def test_valid_png_safe(self) -> None:
        """File PNG hợp lệ (magic bytes PNG: 89 50 4E 47) → SAFE."""
        # Magic bytes PNG thật
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        result = scan_attachment(png_header, "anh.png", FILE_PATH, EMAIL_ID)

        assert result.status == SafetyStatus.SAFE
        assert result.safe_attachment is not None

    def test_valid_txt_safe(self) -> None:
        """File text thông thường → SAFE."""
        data = "Đây là nội dung bài tập môn AI.\n".encode("utf-8")
        result = scan_attachment(data, "baitap.txt", "data/real/e1/baitap.txt", EMAIL_ID)

        assert result.status == SafetyStatus.SAFE
        assert result.safe_attachment is not None

    def test_clean_zip_safe(self) -> None:
        """ZIP sạch (chỉ chứa .txt và .pdf) → SAFE."""
        zip_data = _make_zip({"readme.txt": b"hello", "baocao.pdf": MAGIC_PDF + b"content"})
        result = scan_attachment(zip_data, "archive.zip", "data/real/e1/archive.zip", EMAIL_ID)

        assert result.status == SafetyStatus.SAFE
        assert result.safe_attachment is not None

    def test_empty_file_safe(self) -> None:
        """File 0 byte — không có tín hiệu nguy hiểm → SAFE."""
        result = scan_attachment(b"", "empty.txt", "data/real/e1/empty.txt", EMAIL_ID)

        assert result.status == SafetyStatus.SAFE
        assert result.safe_attachment is not None

    def test_csv_safe(self) -> None:
        """File CSV → SAFE."""
        data = b"ten,diem\nAn,8.5\nBinh,9.0\n"
        result = scan_attachment(data, "diem.csv", "data/real/e1/diem.csv", EMAIL_ID)

        assert result.status == SafetyStatus.SAFE
        assert result.safe_attachment is not None


# ===========================================================================
# NHÓM 2 — Denylist đuôi → MALICIOUS
# ===========================================================================


class TestDangerousExtensions:
    """Đuôi file ∈ DANGEROUS_EXTENSIONS → MALICIOUS, không có SafeAttachment."""

    @pytest.mark.parametrize("ext", [".exe", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".jar", ".lnk", ".dll", ".sys"])
    def test_dangerous_ext_malicious(self, ext: str) -> None:
        """Các đuôi nguy hiểm phổ biến → MALICIOUS."""
        filename = f"file{ext}"
        result = scan_attachment(b"some content", filename, f"data/real/e1/{filename}", EMAIL_ID)

        assert result.status == SafetyStatus.MALICIOUS
        assert result.safe_attachment is None
        assert len(result.reasons) >= 1
        assert ext in result.reasons[0]

    def test_exe_extension_always_malicious(self) -> None:
        """File .exe dù nội dung lành → vẫn MALICIOUS."""
        result = scan_attachment(
            b"not really an exe", "tool.exe", "data/real/e1/tool.exe", EMAIL_ID
        )
        assert result.status == SafetyStatus.MALICIOUS
        assert result.safe_attachment is None

    def test_scr_extension_malicious(self) -> None:
        """.scr (screensaver thực chất là EXE) → MALICIOUS."""
        result = scan_attachment(b"data", "screen.scr", "data/real/e1/screen.scr", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_hta_extension_malicious(self) -> None:
        """.hta (HTML Application) → MALICIOUS."""
        result = scan_attachment(b"<html>", "app.hta", "data/real/e1/app.hta", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_msi_extension_malicious(self) -> None:
        """.msi (Windows Installer) → MALICIOUS."""
        result = scan_attachment(b"msi content", "setup.msi", "data/real/e1/setup.msi", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS


# ===========================================================================
# NHÓM 3 — Đuôi kép → MALICIOUS
# ===========================================================================


class TestDoubleExtensions:
    """Đuôi kép như baitap.pdf.exe → phát hiện đuôi nguy hiểm → MALICIOUS."""

    def test_double_ext_pdf_exe_malicious(self) -> None:
        """baitap.pdf.exe → MALICIOUS (đuôi .exe được phát hiện)."""
        result = scan_attachment(
            b"content", "baitap.pdf.exe", "data/real/e1/baitap.pdf.exe", EMAIL_ID
        )
        assert result.status == SafetyStatus.MALICIOUS
        assert result.safe_attachment is None
        assert ".exe" in result.reasons[0]

    def test_double_ext_txt_bat_malicious(self) -> None:
        """document.txt.bat → MALICIOUS."""
        result = scan_attachment(
            b"@echo off", "document.txt.bat", "data/real/e1/document.txt.bat", EMAIL_ID
        )
        assert result.status == SafetyStatus.MALICIOUS

    def test_double_ext_docx_js_malicious(self) -> None:
        """report.docx.js → MALICIOUS."""
        result = scan_attachment(
            b"alert(1)", "report.docx.js", "data/real/e1/report.docx.js", EMAIL_ID
        )
        assert result.status == SafetyStatus.MALICIOUS

    def test_double_ext_safe_safe_still_safe(self) -> None:
        """file.txt.pdf → đuôi cuối .pdf hợp lệ, không có đuôi nguy hiểm → kiểm tra tiếp."""
        data = MAGIC_PDF + b"content"
        result = scan_attachment(data, "file.txt.pdf", "data/real/e1/file.txt.pdf", EMAIL_ID)
        # Không có đuôi nguy hiểm, PDF header hợp lệ → SAFE
        assert result.status == SafetyStatus.SAFE


# ===========================================================================
# NHÓM 4 — Magic bytes thực thi → MALICIOUS
# ===========================================================================


class TestMagicBytes:
    """Magic bytes PE/ELF/Mach-O → MALICIOUS dù đuôi file lành."""

    def test_pe_magic_disguised_as_pdf_malicious(self) -> None:
        """MZ magic nhưng tên file .pdf → MALICIOUS (giả danh tài liệu)."""
        data = MAGIC_PE + b"\x00" * 100
        result = scan_attachment(data, "report.pdf", "data/real/e1/report.pdf", EMAIL_ID)

        assert result.status == SafetyStatus.MALICIOUS
        assert result.safe_attachment is None
        # Thông báo phải đề cập đến giả danh / giả mạo
        assert any("giả" in r.lower() for r in result.reasons)

    def test_pe_magic_disguised_as_docx_malicious(self) -> None:
        """MZ magic nhưng tên .docx → MALICIOUS."""
        data = MAGIC_PE + b"\x00" * 50
        result = scan_attachment(data, "bai_tap.docx", "data/real/e1/bai_tap.docx", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_pe_magic_disguised_as_jpg_malicious(self) -> None:
        """MZ magic nhưng tên .jpg → MALICIOUS."""
        data = MAGIC_PE + b"\x00" * 50
        result = scan_attachment(data, "photo.jpg", "data/real/e1/photo.jpg", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_pe_magic_disguised_as_txt_malicious(self) -> None:
        """MZ magic nhưng tên .txt → MALICIOUS."""
        data = MAGIC_PE + b"\x00" * 50
        result = scan_attachment(data, "note.txt", "data/real/e1/note.txt", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_elf_magic_in_pdf_malicious(self) -> None:
        """ELF magic nhưng tên .pdf → MALICIOUS."""
        data = MAGIC_ELF + b"\x00" * 100
        result = scan_attachment(data, "baocao.pdf", FILE_PATH, EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS
        assert result.safe_attachment is None

    def test_elf_magic_no_ext_malicious(self) -> None:
        """ELF magic, đuôi không phải document → MALICIOUS."""
        data = MAGIC_ELF + b"\x00" * 50
        result = scan_attachment(data, "binary_file", "data/real/e1/binary_file", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_macho1_magic_malicious(self) -> None:
        """Mach-O little-endian magic → MALICIOUS."""
        data = MAGIC_MACHO1 + b"\x00" * 50
        result = scan_attachment(data, "macos_app.pdf", FILE_PATH, EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_macho2_magic_malicious(self) -> None:
        """Mach-O big-endian magic → MALICIOUS."""
        data = MAGIC_MACHO2 + b"\x00" * 50
        result = scan_attachment(data, "macos_app.docx", "data/real/e1/macos_app.docx", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_pe_magic_on_exe_still_malicious(self) -> None:
        """MZ magic + .exe extension → MALICIOUS (denylist chặn trước magic bytes)."""
        data = MAGIC_PE + b"\x00" * 50
        result = scan_attachment(data, "real.exe", "data/real/e1/real.exe", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_normal_pdf_not_flagged_as_exe(self) -> None:
        """%PDF- header → không bị nhầm là file thực thi."""
        data = MAGIC_PDF + b"1.7 real pdf\n%%EOF"
        result = scan_attachment(data, "real.pdf", FILE_PATH, EMAIL_ID)
        assert result.status == SafetyStatus.SAFE


# ===========================================================================
# NHÓM 5 — PDF header mismatch → SUSPICIOUS
# ===========================================================================


class TestPdfHeaderMismatch:
    """File .pdf nhưng header không phải %PDF- → SUSPICIOUS."""

    def test_pdf_wrong_header_suspicious(self) -> None:
        """File .pdf bắt đầu bằng nội dung lạ → SUSPICIOUS."""
        data = b"WRONG" + b" fake content"
        result = scan_attachment(data, "baocao.pdf", FILE_PATH, EMAIL_ID)

        assert result.status == SafetyStatus.SUSPICIOUS
        assert result.safe_attachment is None
        assert len(result.reasons) >= 1

    def test_pdf_starts_with_html_suspicious(self) -> None:
        """File .pdf thực chất là HTML bên trong → SUSPICIOUS."""
        data = b"<html><body>Phishing page</body></html>"
        result = scan_attachment(data, "dangky.pdf", FILE_PATH, EMAIL_ID)
        assert result.status == SafetyStatus.SUSPICIOUS

    def test_pdf_too_short_suspicious(self) -> None:
        """File .pdf chỉ có 3 byte → header không đủ → SUSPICIOUS."""
        result = scan_attachment(b"PDF", "short.pdf", FILE_PATH, EMAIL_ID)
        assert result.status == SafetyStatus.SUSPICIOUS

    def test_pdf_valid_header_safe(self) -> None:
        """File .pdf đúng header %PDF- → SAFE."""
        data = MAGIC_PDF + b"1.4 valid pdf\n"
        result = scan_attachment(data, "valid.pdf", FILE_PATH, EMAIL_ID)
        assert result.status == SafetyStatus.SAFE


# ===========================================================================
# NHÓM 6 — ZIP với nội dung nguy hiểm → MALICIOUS
# ===========================================================================


class TestZipContents:
    """Kiểm tra nội dung file ZIP."""

    def test_zip_with_bat_inside_malicious(self) -> None:
        """ZIP chứa file .bat → MALICIOUS."""
        zip_data = _make_zip({"readme.txt": b"safe", "run.bat": b"@echo off\ndel /f *"})
        result = scan_attachment(zip_data, "bundle.zip", "data/real/e1/bundle.zip", EMAIL_ID)

        assert result.status == SafetyStatus.MALICIOUS
        assert result.safe_attachment is None
        assert any("run.bat" in r for r in result.reasons)

    def test_zip_with_exe_inside_malicious(self) -> None:
        """ZIP chứa file .exe → MALICIOUS."""
        zip_data = _make_zip({"docs/setup.exe": b"MZ fake"})
        result = scan_attachment(zip_data, "package.zip", "data/real/e1/package.zip", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_zip_with_ps1_inside_malicious(self) -> None:
        """ZIP chứa file .ps1 (PowerShell) → MALICIOUS."""
        zip_data = _make_zip({"scripts/deploy.ps1": b"Remove-Item -Force"})
        result = scan_attachment(zip_data, "scripts.zip", "data/real/e1/scripts.zip", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_zip_with_js_inside_malicious(self) -> None:
        """ZIP chứa file .js → MALICIOUS."""
        zip_data = _make_zip({"payload.js": b"eval(atob('...'))"})
        result = scan_attachment(zip_data, "files.zip", "data/real/e1/files.zip", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_zip_clean_safe(self) -> None:
        """ZIP chỉ chứa file tài liệu thường → SAFE."""
        zip_data = _make_zip(
            {
                "baocao.txt": b"content",
                "huong_dan.pdf": MAGIC_PDF + b"content",
                "data.csv": b"a,b\n1,2",
            }
        )
        result = scan_attachment(zip_data, "files.zip", "data/real/e1/files.zip", EMAIL_ID)
        assert result.status == SafetyStatus.SAFE
        assert result.safe_attachment is not None

    def test_zip_password_protected_suspicious(self) -> None:
        """ZIP có mật khẩu → không thể kiểm tra nội dung → SUSPICIOUS."""
        zip_data = _make_zip({"secret.txt": b"secret content"}, password=b"pass123")
        result = scan_attachment(
            zip_data, "encrypted.zip", "data/real/e1/encrypted.zip", EMAIL_ID
        )
        assert result.status == SafetyStatus.SUSPICIOUS
        assert result.safe_attachment is None
        assert any("mật khẩu" in r.lower() for r in result.reasons)

    def test_bad_zip_file_suspicious(self) -> None:
        """Dữ liệu tên .zip nhưng không phải ZIP thật → SUSPICIOUS."""
        result = scan_attachment(
            b"this is not a zip", "fake.zip", "data/real/e1/fake.zip", EMAIL_ID
        )
        assert result.status == SafetyStatus.SUSPICIOUS


# ===========================================================================
# NHÓM 7 — Đuôi SUSPICIOUS (macro, nén khác, HTML)
# ===========================================================================


class TestSuspiciousExtensions:
    """Đuôi macro / nén / HTML → SUSPICIOUS (không phải MALICIOUS)."""

    @pytest.mark.parametrize("ext", [".docm", ".xlsm", ".pptm"])
    def test_macro_ext_suspicious(self, ext: str) -> None:
        """Định dạng có macro → SUSPICIOUS."""
        filename = f"document{ext}"
        result = scan_attachment(b"content", filename, f"data/real/e1/{filename}", EMAIL_ID)

        assert result.status == SafetyStatus.SUSPICIOUS
        assert result.safe_attachment is None
        assert len(result.reasons) >= 1

    @pytest.mark.parametrize("ext", [".rar", ".7z"])
    def test_compressed_ext_suspicious(self, ext: str) -> None:
        """Định dạng nén không hỗ trợ kiểm tra nội dung → SUSPICIOUS."""
        filename = f"archive{ext}"
        result = scan_attachment(b"content", filename, f"data/real/e1/{filename}", EMAIL_ID)
        assert result.status == SafetyStatus.SUSPICIOUS

    @pytest.mark.parametrize("ext", [".html", ".htm"])
    def test_html_ext_suspicious(self, ext: str) -> None:
        """Định dạng HTML → SUSPICIOUS (có thể chứa script)."""
        filename = f"page{ext}"
        result = scan_attachment(
            b"<html><script>alert(1)</script></html>",
            filename,
            f"data/real/e1/{filename}",
            EMAIL_ID,
        )
        assert result.status == SafetyStatus.SUSPICIOUS


# ===========================================================================
# NHÓM 8 — Giới hạn kích thước → SUSPICIOUS
# ===========================================================================


class TestSizeLimit:
    """File vượt giới hạn kích thước → SUSPICIOUS (không kiểm tra tiếp)."""

    def test_file_too_large_suspicious(self) -> None:
        """File 1 byte vượt max → SUSPICIOUS."""
        max_b = 100
        data = b"X" * (max_b + 1)
        result = scan_attachment(
            data, "big.pdf", FILE_PATH, EMAIL_ID, max_bytes=max_b
        )
        assert result.status == SafetyStatus.SUSPICIOUS
        assert result.safe_attachment is None
        assert len(result.reasons) >= 1

    def test_file_exactly_max_safe(self) -> None:
        """File đúng max bytes → không bị chặn kích thước."""
        max_b = 50
        # Dùng file .txt để tránh các kiểm tra khác
        data = b"A" * max_b
        result = scan_attachment(
            data, "exact.txt", "data/real/e1/exact.txt", EMAIL_ID, max_bytes=max_b
        )
        # Không bị chặn kích thước (len == max, không phải >)
        assert result.status != SafetyStatus.SUSPICIOUS or "kích thước" not in (
            result.reasons[0] if result.reasons else ""
        )

    def test_large_file_skips_magic_check(self) -> None:
        """File quá lớn → trả về SUSPICIOUS ngay, không chạy kiểm tra magic bytes."""
        # Dù nội dung có MZ magic, nếu kích thước vượt → chặn vì kích thước
        max_b = 10
        data = MAGIC_PE + b"\x00" * 20  # 22 bytes > 10
        result = scan_attachment(
            data, "big.pdf", FILE_PATH, EMAIL_ID, max_bytes=max_b
        )
        assert result.status == SafetyStatus.SUSPICIOUS
        assert any("kích thước" in r.lower() or "giới hạn" in r.lower() for r in result.reasons)


# ===========================================================================
# NHÓM 9 — allow_suspicious flag
# ===========================================================================


class TestAllowSuspicious:
    """Kiểm tra cờ allow_suspicious."""

    def test_suspicious_without_flag_no_safe_attachment(self) -> None:
        """SUSPICIOUS + allow_suspicious=False → safe_attachment = None."""
        data = b"<html>phishing</html>"
        result = scan_attachment(
            data, "page.html", "data/real/e1/page.html", EMAIL_ID, allow_suspicious=False
        )
        assert result.status == SafetyStatus.SUSPICIOUS
        assert result.safe_attachment is None

    def test_suspicious_with_flag_has_safe_attachment(self) -> None:
        """SUSPICIOUS + allow_suspicious=True → safe_attachment được tạo."""
        data = b"<html>content</html>"
        result = scan_attachment(
            data, "page.html", "data/real/e1/page.html", EMAIL_ID, allow_suspicious=True
        )
        assert result.status == SafetyStatus.SUSPICIOUS
        assert result.safe_attachment is not None
        assert isinstance(result.safe_attachment, SafeAttachment)

    def test_malicious_with_flag_still_no_safe_attachment(self) -> None:
        """MALICIOUS + allow_suspicious=True → vẫn không có safe_attachment."""
        data = MAGIC_PE + b"\x00" * 50
        result = scan_attachment(
            data, "virus.pdf", FILE_PATH, EMAIL_ID, allow_suspicious=True
        )
        assert result.status == SafetyStatus.MALICIOUS
        assert result.safe_attachment is None

    def test_safe_with_flag_has_safe_attachment(self) -> None:
        """SAFE + allow_suspicious=True → safe_attachment vẫn được tạo bình thường."""
        data = MAGIC_PDF + b"valid content"
        result = scan_attachment(
            data, "baocao.pdf", FILE_PATH, EMAIL_ID, allow_suspicious=True
        )
        assert result.status == SafetyStatus.SAFE
        assert result.safe_attachment is not None

    def test_pdf_mismatch_with_flag_has_safe_attachment(self) -> None:
        """PDF header sai + allow_suspicious=True → safe_attachment được tạo."""
        result = scan_attachment(
            b"WRONG header content",
            "baocao.pdf",
            FILE_PATH,
            EMAIL_ID,
            allow_suspicious=True,
        )
        assert result.status == SafetyStatus.SUSPICIOUS
        assert result.safe_attachment is not None


# ===========================================================================
# NHÓM 10 — SHA-256 format
# ===========================================================================


class TestSha256Format:
    """Mã băm SHA-256 luôn đúng định dạng: 64 ký tự hex chữ thường."""

    def test_sha256_format_safe_file(self) -> None:
        """SHA-256 trả về đúng định dạng cho file SAFE."""
        data = MAGIC_PDF + b"content"
        result = scan_attachment(data, "file.pdf", FILE_PATH, EMAIL_ID)
        assert len(result.sha256) == 64
        assert result.sha256 == result.sha256.lower()
        assert all(c in "0123456789abcdef" for c in result.sha256)

    def test_sha256_format_malicious_file(self) -> None:
        """SHA-256 trả về đúng định dạng ngay cả cho file MALICIOUS."""
        data = b"MZ fake exe"
        result = scan_attachment(data, "virus.exe", "data/real/e1/virus.exe", EMAIL_ID)
        assert len(result.sha256) == 64
        assert result.sha256 == result.sha256.lower()

    def test_sha256_matches_actual_hash(self) -> None:
        """SHA-256 trong kết quả khớp với giá trị tính độc lập."""
        data = b"Test content for SHA-256 verification"
        expected = hashlib.sha256(data).hexdigest()
        result = scan_attachment(data, "test.txt", "data/real/e1/test.txt", EMAIL_ID)
        assert result.sha256 == expected

    def test_sha256_in_safe_attachment_matches(self) -> None:
        """SHA-256 trong SafeAttachment khớp với sha256 trong AttachmentScanResult."""
        data = MAGIC_PDF + b"valid pdf content"
        result = scan_attachment(data, "baocao.pdf", FILE_PATH, EMAIL_ID)
        assert result.safe_attachment is not None
        assert result.safe_attachment.sha256 == result.sha256

    def test_empty_file_sha256_valid(self) -> None:
        """File rỗng → SHA-256 vẫn hợp lệ (SHA-256 của empty bytes)."""
        expected = hashlib.sha256(b"").hexdigest()
        result = scan_attachment(b"", "empty.txt", "data/real/e1/empty.txt", EMAIL_ID)
        assert result.sha256 == expected


# ===========================================================================
# NHÓM 11 — Thuộc tính kết quả (fields)
# ===========================================================================


class TestResultFields:
    """Kiểm tra các trường của AttachmentScanResult."""

    def test_result_has_correct_filename(self) -> None:
        """filename trong kết quả khớp với tham số đầu vào."""
        result = scan_attachment(b"content", "baocao.txt", FILE_PATH, EMAIL_ID)
        assert result.filename == "baocao.txt"

    def test_result_has_correct_file_path(self) -> None:
        """file_path trong kết quả khớp với tham số đầu vào."""
        path = "data/real/email-001/abc123_baocao.pdf"
        result = scan_attachment(MAGIC_PDF + b"content", "baocao.pdf", path, EMAIL_ID)
        assert result.file_path == path

    def test_safe_attachment_has_correct_email_id(self) -> None:
        """email_id trong SafeAttachment khớp với tham số đầu vào."""
        result = scan_attachment(MAGIC_PDF + b"content", "file.pdf", FILE_PATH, EMAIL_ID)
        assert result.safe_attachment is not None
        assert result.safe_attachment.email_id == EMAIL_ID

    def test_safe_attachment_has_correct_path(self) -> None:
        """path trong SafeAttachment khớp với file_path."""
        path = "data/real/email-002/abc_file.pdf"
        result = scan_attachment(MAGIC_PDF + b"data", "file.pdf", path, EMAIL_ID)
        assert result.safe_attachment is not None
        assert result.safe_attachment.path == path

    def test_malicious_has_no_safe_attachment(self) -> None:
        """Mọi kết quả MALICIOUS đều không có safe_attachment."""
        cases = [
            (b"MZ\x00\x00", "file.exe"),
            (MAGIC_ELF, "file.pdf"),
            (b"content", "virus.bat"),
        ]
        for data, fname in cases:
            result = scan_attachment(data, fname, f"data/real/e1/{fname}", EMAIL_ID)
            assert result.status == SafetyStatus.MALICIOUS
            assert result.safe_attachment is None, f"Failed for {fname}"

    def test_reasons_is_list(self) -> None:
        """reasons luôn là list (có thể rỗng)."""
        result = scan_attachment(MAGIC_PDF + b"content", "file.pdf", FILE_PATH, EMAIL_ID)
        assert isinstance(result.reasons, list)

    def test_reasons_empty_for_safe(self) -> None:
        """File SAFE không có reasons."""
        result = scan_attachment(MAGIC_PDF + b"content", "file.pdf", FILE_PATH, EMAIL_ID)
        assert result.reasons == []


# ===========================================================================
# NHÓM 12 — Helper function: _sha256_hex
# ===========================================================================


class TestSha256Helper:
    """Kiểm tra hàm _sha256_hex nội bộ."""

    def test_sha256_hex_known_value(self) -> None:
        """Giá trị SHA-256 biết trước của chuỗi rỗng."""
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert _sha256_hex(b"") == expected

    def test_sha256_hex_always_lowercase(self) -> None:
        """_sha256_hex luôn trả về chữ thường."""
        result = _sha256_hex(b"Hello World")
        assert result == result.lower()

    def test_sha256_hex_length(self) -> None:
        """_sha256_hex luôn trả về đúng 64 ký tự."""
        for data in [b"", b"a", b"x" * 1000]:
            assert len(_sha256_hex(data)) == 64


# ===========================================================================
# NHÓM 13 — to_finding() method
# ===========================================================================


class TestToFinding:
    """Kiểm tra chuyển đổi sang AttachmentFinding."""

    def test_to_finding_safe_file(self) -> None:
        """to_finding() hoạt động cho file SAFE."""
        from modules.email_security.models import AttachmentFinding

        data = MAGIC_PDF + b"content"
        result = scan_attachment(data, "baocao.pdf", FILE_PATH, EMAIL_ID)
        finding = result.to_finding()

        assert isinstance(finding, AttachmentFinding)
        assert finding.filename == "baocao.pdf"
        assert finding.path == FILE_PATH
        assert finding.sha256 == result.sha256
        assert finding.status == SafetyStatus.SAFE

    def test_to_finding_malicious_has_reasons(self) -> None:
        """to_finding() cho file MALICIOUS có reasons."""
        result = scan_attachment(b"content", "virus.exe", "data/real/e1/virus.exe", EMAIL_ID)
        finding = result.to_finding()

        assert finding.status == SafetyStatus.MALICIOUS
        assert len(finding.reasons) >= 1
        assert finding.reasons[0].code != ""


# ===========================================================================
# NHÓM 14 — Edge cases & kiểm tra bổ sung
# ===========================================================================


class TestEdgeCases:
    """Các trường hợp biên và đặc biệt."""

    def test_filename_uppercase_ext_detected(self) -> None:
        """Đuôi file chữ hoa (.EXE, .PDF) vẫn được nhận dạng đúng."""
        result = scan_attachment(b"content", "VIRUS.EXE", "data/real/e1/VIRUS.EXE", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_filename_mixed_case_pdf_header_check(self) -> None:
        """File .PDF (hoa) với header hợp lệ → SAFE."""
        data = MAGIC_PDF + b"valid content"
        result = scan_attachment(data, "REPORT.PDF", "data/real/e1/REPORT.PDF", EMAIL_ID)
        assert result.status == SafetyStatus.SAFE

    def test_no_extension_file_safe(self) -> None:
        """File không có đuôi, nội dung thường → không có rule nào khớp → SAFE."""
        result = scan_attachment(
            b"just some text content",
            "README",
            "data/real/e1/README",
            EMAIL_ID,
        )
        assert result.status == SafetyStatus.SAFE

    def test_pe_magic_on_no_ext_file_malicious(self) -> None:
        """MZ magic + file không có đuôi → MALICIOUS (vẫn là file thực thi)."""
        data = MAGIC_PE + b"\x00" * 20
        result = scan_attachment(data, "binary", "data/real/e1/binary", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_zip_nested_dangerous_file_malicious(self) -> None:
        """ZIP chứa file .exe trong subfolder → MALICIOUS."""
        zip_data = _make_zip({"subfolder/evil/payload.exe": b"MZ content"})
        result = scan_attachment(zip_data, "nested.zip", "data/real/e1/nested.zip", EMAIL_ID)
        assert result.status == SafetyStatus.MALICIOUS

    def test_scan_result_is_dataclass(self) -> None:
        """Kết quả trả về là AttachmentScanResult."""
        result = scan_attachment(b"content", "file.txt", "data/real/e1/file.txt", EMAIL_ID)
        assert isinstance(result, AttachmentScanResult)

    def test_dangerous_extensions_set_contains_expected(self) -> None:
        """DANGEROUS_EXTENSIONS chứa các đuôi theo yêu cầu đề bài."""
        required = {".exe", ".bat", ".cmd", ".com", ".scr", ".pif",
                    ".vbs", ".vbe", ".js", ".jse", ".wsf", ".wsh",
                    ".ps1", ".msi", ".msp", ".hta", ".cpl", ".jar",
                    ".reg", ".lnk", ".dll", ".sys"}
        assert required.issubset(DANGEROUS_EXTENSIONS)

    def test_suspicious_extensions_set_contains_expected(self) -> None:
        """SUSPICIOUS_EXTENSIONS chứa các đuôi theo yêu cầu đề bài."""
        required = {".docm", ".xlsm", ".pptm", ".zip", ".rar", ".7z", ".html", ".htm"}
        assert required.issubset(SUSPICIOUS_EXTENSIONS)

    def test_scan_multiple_files_independent(self) -> None:
        """Nhiều lần gọi scan_attachment độc lập nhau (không chia sẻ trạng thái)."""
        clean = scan_attachment(MAGIC_PDF + b"content", "clean.pdf", FILE_PATH, EMAIL_ID)
        malicious = scan_attachment(b"content", "virus.exe", "data/real/e1/virus.exe", EMAIL_ID)
        assert clean.status == SafetyStatus.SAFE
        assert malicious.status == SafetyStatus.MALICIOUS
        # Kết quả độc lập, không ảnh hưởng nhau
        assert clean.safe_attachment is not None
        assert malicious.safe_attachment is None

    def test_pdf_exactly_5_bytes_valid_header_safe(self) -> None:
        """File PDF chỉ có đúng 5 byte '%PDF-' → header hợp lệ → SAFE."""
        data = MAGIC_PDF  # chính xác 5 byte
        result = scan_attachment(data, "minimal.pdf", FILE_PATH, EMAIL_ID)
        assert result.status == SafetyStatus.SAFE

    def test_docx_safe_no_macro(self) -> None:
        """.docx (không phải .docm) → không có lý do SUSPICIOUS → SAFE."""
        data = b"PK\x03\x04" + b"\x00" * 50  # ZIP magic (docx là ZIP)
        # .docx không trong SUSPICIOUS_EXTENSIONS nên sẽ được kiểm tra như file thường
        # Tuy nhiên nội dung không phải exe magic → SAFE
        result = scan_attachment(data, "baitap.docx", "data/real/e1/baitap.docx", EMAIL_ID)
        # .docx không phải ZIP final_ext nên không kiểm tra nội dung ZIP
        assert result.status == SafetyStatus.SAFE
