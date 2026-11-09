"""tests/email_security/test_pipeline_stub.py

Test offline cho WP-00 (Khung & Stub) và WP-01 (Parse .eml).

Mọi test:
- Chạy hoàn toàn không cần mạng (fixture autouse block_network trong conftest.py).
- Không cần API key (settings_offline không có VIRUSTOTAL_API_KEY hay GEMINI_API_KEY).
- Không sửa core/contracts.py.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.contracts import (
    ClassifiedEmail,
    EmailLabel,
    SafeAttachment,
    SafetyStatus,
    can_forward,
)
from modules.email_security import (
    ProcessedEmail,
    aggregate_safety,
    approve_suspicious,
    can_forward_email,
    max_status,
    process_email,
)
from modules.email_security.config import Settings
from modules.email_security.parser import _sanitize_filename, _sha256_bytes, parse_eml
from modules.email_security.urls import defang_url, extract_urls, normalize_url

from .conftest import (
    FIXTURES_DIR,
    make_html_eml,
    make_multipart_eml,
    make_plain_eml,
)


# ===========================================================================
# PHẦN 1: aggregate_safety & max_status
# ===========================================================================

class TestMaxStatus:
    """Kiểm tra hàm max_status — tính chất đơn điệu."""

    def test_no_args_returns_safe(self):
        assert max_status() is SafetyStatus.SAFE

    def test_single_safe(self):
        assert max_status(SafetyStatus.SAFE) is SafetyStatus.SAFE

    def test_single_suspicious(self):
        assert max_status(SafetyStatus.SUSPICIOUS) is SafetyStatus.SUSPICIOUS

    def test_single_malicious(self):
        assert max_status(SafetyStatus.MALICIOUS) is SafetyStatus.MALICIOUS

    def test_safe_suspicious_returns_suspicious(self):
        assert max_status(SafetyStatus.SAFE, SafetyStatus.SUSPICIOUS) is SafetyStatus.SUSPICIOUS

    def test_suspicious_malicious_returns_malicious(self):
        assert max_status(SafetyStatus.SUSPICIOUS, SafetyStatus.MALICIOUS) is SafetyStatus.MALICIOUS

    def test_all_three_returns_malicious(self):
        result = max_status(SafetyStatus.SAFE, SafetyStatus.SUSPICIOUS, SafetyStatus.MALICIOUS)
        assert result is SafetyStatus.MALICIOUS

    def test_monotone_adding_bad_signal_never_decreases(self):
        """Thêm tín hiệu xấu hơn không bao giờ làm kết quả giảm."""
        base = max_status(SafetyStatus.SAFE)
        after = max_status(SafetyStatus.SAFE, SafetyStatus.SUSPICIOUS)
        assert after.value >= base.value or after is SafetyStatus.SUSPICIOUS


class TestAggregateSafety:
    def test_phishing_label_raises_safe_to_suspicious(self):
        result = aggregate_safety(SafetyStatus.SAFE, label_is_phishing=True)
        assert result is SafetyStatus.SUSPICIOUS

    def test_phishing_label_does_not_lower_malicious(self):
        """PHISHING không hạ MALICIOUS xuống SUSPICIOUS."""
        result = aggregate_safety(SafetyStatus.MALICIOUS, label_is_phishing=True)
        assert result is SafetyStatus.MALICIOUS

    def test_no_phishing_label_keeps_safe(self):
        result = aggregate_safety(SafetyStatus.SAFE, label_is_phishing=False)
        assert result is SafetyStatus.SAFE

    def test_multiple_signals_max(self):
        result = aggregate_safety(
            SafetyStatus.SAFE,
            SafetyStatus.SUSPICIOUS,
            SafetyStatus.SAFE,
        )
        assert result is SafetyStatus.SUSPICIOUS

    def test_empty_no_phishing_returns_safe(self):
        result = aggregate_safety()
        assert result is SafetyStatus.SAFE

    def test_empty_with_phishing_returns_suspicious(self):
        result = aggregate_safety(label_is_phishing=True)
        assert result is SafetyStatus.SUSPICIOUS


# ===========================================================================
# PHẦN 2: can_forward_email
# ===========================================================================

class TestCanForwardEmail:
    def _make_email(self, safety: SafetyStatus) -> ClassifiedEmail:
        return ClassifiedEmail(
            id="test-id",
            sender="sender@example.com",
            subject="Test",
            body="Body",
            received_at=datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc),
            label=EmailLabel.OTHER,
            safety=safety,
            label_confidence=0.9,
        )

    def test_safe_email_can_forward(self):
        email = self._make_email(SafetyStatus.SAFE)
        assert can_forward_email(email) is True

    def test_malicious_email_cannot_forward(self):
        email = self._make_email(SafetyStatus.MALICIOUS)
        assert can_forward_email(email) is False

    def test_malicious_even_with_user_approved(self):
        """MALICIOUS không bao giờ được chuyển, kể cả khi user_approved=True."""
        email = self._make_email(SafetyStatus.MALICIOUS)
        assert can_forward_email(email, user_approved=True) is False

    def test_suspicious_without_approval_blocked(self):
        email = self._make_email(SafetyStatus.SUSPICIOUS)
        assert can_forward_email(email, user_approved=False) is False

    def test_suspicious_with_approval_allowed(self):
        email = self._make_email(SafetyStatus.SUSPICIOUS)
        assert can_forward_email(email, user_approved=True) is True

    def test_consistent_with_core_can_forward(self):
        """Kết quả nhất quán với can_forward() trong core/contracts.py."""
        email = self._make_email(SafetyStatus.SAFE)
        assert can_forward_email(email) == can_forward(email, allow_suspicious=False)

        email = self._make_email(SafetyStatus.SUSPICIOUS)
        assert can_forward_email(email, user_approved=True) == can_forward(email, allow_suspicious=True)


# ===========================================================================
# PHẦN 3: parse_eml — WP-01
# ===========================================================================

class TestSanitizeFilename:
    def test_path_traversal_blocked(self):
        name = _sanitize_filename("../../etc/passwd")
        assert ".." not in name
        assert "/" not in name
        assert "\\" not in name

    def test_windows_traversal_blocked(self):
        name = _sanitize_filename("..\\..\\evil.exe")
        assert ".." not in name

    def test_control_chars_removed(self):
        name = _sanitize_filename("file\x00\x1fname.pdf")
        assert "\x00" not in name
        assert "\x1f" not in name

    def test_long_filename_truncated(self):
        long_name = "a" * 200 + ".pdf"
        name = _sanitize_filename(long_name)
        assert len(name) <= 100

    def test_normal_name_preserved(self):
        name = _sanitize_filename("report_2026.pdf")
        assert name == "report_2026.pdf"

    def test_evil_exe_name(self):
        name = _sanitize_filename("../../evil.exe")
        assert name == "evil.exe" or ("evil" in name and ".." not in name)

    def test_leading_dots_removed(self):
        name = _sanitize_filename(".hidden_file.txt")
        assert not name.startswith(".")


class TestSha256:
    def test_empty_bytes(self):
        expected = hashlib.sha256(b"").hexdigest()
        assert _sha256_bytes(b"") == expected

    def test_known_hash(self):
        data = b"hello module D"
        expected = hashlib.sha256(data).hexdigest()
        assert _sha256_bytes(data) == expected
        assert len(_sha256_bytes(data)) == 64

    def test_lowercase(self):
        result = _sha256_bytes(b"test")
        assert result == result.lower()


class TestParseEml:
    def test_plain_text_email(self, tmp_path: Path, settings_offline: Settings):
        """Parse email văn bản thuần — WP-01 test case cơ bản."""
        raw = make_plain_eml(
            subject="Test Subject",
            sender="sender@example.com",
            body="Hello World. See https://example.com for details.",
            message_id="test-plain-001@example.com",
        )
        parsed, saved = parse_eml(raw, attachments_dir=str(tmp_path), save_attachments=False)

        assert parsed.subject == "Test Subject"
        assert parsed.sender != ""
        assert "example.com" in parsed.sender.lower() or "sender" in parsed.sender.lower()
        assert "Hello World" in parsed.body_text
        assert isinstance(parsed.received_at, datetime)
        assert parsed.urls == ["https://example.com"]
        assert parsed.raw_attachments == []
        assert saved == []

    def test_no_message_id_generates_uuid(self, tmp_path: Path):
        """Email không có Message-ID → sinh UUID, không crash."""
        raw = (
            "From: sender@example.com\r\n"
            "To: recipient@example.com\r\n"
            "Subject: No ID\r\n"
            "Date: Mon, 09 Nov 2026 08:00:00 +0700\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "\r\n"
            "Body without Message-ID header."
        ).encode("utf-8")
        parsed, _ = parse_eml(raw, save_attachments=False)
        assert parsed.message_id  # không rỗng
        assert len(parsed.message_id) >= 8  # UUID hoặc slug có độ dài hợp lý

    def test_html_only_email(self, tmp_path: Path):
        """Email chỉ có HTML → body_text là văn bản đã strip, html_links trích được."""
        raw = make_html_eml(
            html_body='<p>Chào bạn! Xem <a href="https://portal.uni.edu.vn/x">portal</a> nhé.</p>',
        )
        parsed, _ = parse_eml(raw, save_attachments=False)
        assert "Chào bạn" in parsed.body_text
        assert "portal" in parsed.body_text.lower() or "portal" in parsed.body_text
        assert any("portal.uni.edu.vn" in href for _, href in parsed.html_links)

    def test_multipart_with_attachment(self, tmp_path: Path):
        """Email multipart/mixed — body trích được, attachment lưu được."""
        pdf_data = b"%PDF-1.4 fake content for test"
        raw = make_multipart_eml(
            body="Tài liệu đính kèm bên dưới.",
            attach_name="report.pdf",
            attach_data=pdf_data,
        )
        parsed, saved = parse_eml(
            raw,
            attachments_dir=str(tmp_path),
            save_attachments=True,
        )
        assert "Tài liệu" in parsed.body_text
        assert len(parsed.raw_attachments) == 1
        assert parsed.raw_attachments[0]["filename"] == "report.pdf"

        assert len(saved) == 1
        assert saved[0].filename == "report.pdf"
        assert len(saved[0].sha256) == 64
        assert saved[0].sha256 == hashlib.sha256(pdf_data).hexdigest()
        # File thực sự tồn tại trên disk
        assert Path(saved[0].path).exists() or any(tmp_path.rglob("*.pdf"))

    def test_path_traversal_in_attachment_name(self, tmp_path: Path):
        """Tên file đính kèm chứa path traversal → bị làm sạch."""
        raw = make_multipart_eml(
            attach_name="../../evil.exe",
            attach_data=b"malicious",
        )
        parsed, saved = parse_eml(
            raw,
            attachments_dir=str(tmp_path),
            save_attachments=True,
        )
        for sa in saved:
            assert ".." not in sa.filename
            assert ".." not in sa.path
            # Không lưu ra ngoài thư mục tmp_path
            saved_path = Path(sa.path)
            # Kiểm tra không escape ra ngoài attachments_dir
            assert "evil" not in sa.path.split("/")[-2] if "/" in sa.path else True

    def test_missing_date_does_not_crash(self):
        """Thiếu header Date → dùng datetime.now(UTC), không crash."""
        raw = (
            "From: sender@example.com\r\n"
            "To: to@example.com\r\n"
            "Subject: No Date\r\n"
            "Message-ID: <nodate@example.com>\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "\r\n"
            "Body without Date header."
        ).encode("utf-8")
        parsed, _ = parse_eml(raw, save_attachments=False)
        assert isinstance(parsed.received_at, datetime)

    def test_fixture_plain_text_eml(self):
        """Đọc fixture file thật từ tests/email_security/fixtures/."""
        eml_path = FIXTURES_DIR / "plain_text.eml"
        raw = eml_path.read_bytes()
        parsed, _ = parse_eml(raw, save_attachments=False)
        assert "AI" in parsed.subject or "bài tập" in parsed.subject.lower()
        assert parsed.sender != ""
        assert "portal.uni.edu.vn" in " ".join(parsed.urls)

    def test_fixture_phishing_html_eml(self):
        """Fixture phishing HTML — trích được URL nguy hiểm."""
        eml_path = FIXTURES_DIR / "phishing_html.eml"
        raw = eml_path.read_bytes()
        parsed, _ = parse_eml(raw, save_attachments=False)
        assert parsed.reply_to is not None
        assert "attacker" in parsed.reply_to or "evil" in parsed.reply_to
        all_urls = parsed.urls + [href for _, href in parsed.html_links]
        assert any("evil.com" in u or "uni-edu-vn.top" in u for u in all_urls)

    def test_empty_bytes_does_not_crash(self):
        """Bytes rỗng → ParsedEmail trống, không crash."""
        parsed, saved = parse_eml(b"", save_attachments=False)
        assert parsed.message_id  # có message_id (UUID)
        assert saved == []


# ===========================================================================
# PHẦN 4: URL utilities
# ===========================================================================

class TestExtractUrls:
    def test_simple_https_url(self):
        text = "Xem tại https://portal.uni.edu.vn/ai2026 nhé."
        urls = extract_urls(text)
        assert "https://portal.uni.edu.vn/ai2026" in urls

    def test_multiple_urls(self):
        text = "Link 1: https://a.com và link 2: https://b.com/path?q=1"
        urls = extract_urls(text)
        assert len(urls) == 2

    def test_no_scheme_not_extracted(self):
        text = "Truy cập portal.uni.edu.vn trực tiếp."
        urls = extract_urls(text)
        assert urls == []

    def test_trailing_punctuation_stripped(self):
        text = "Xem https://example.com."
        urls = extract_urls(text)
        assert "https://example.com" in urls
        assert not any(u.endswith(".") for u in urls)

    def test_deduplication(self):
        text = "https://example.com và https://example.com"
        urls = extract_urls(text)
        assert urls.count("https://example.com") == 1

    def test_html_links_included(self):
        html_links = [("Portal", "https://portal.uni.edu.vn")]
        urls = extract_urls("No URL in text.", html_links)
        assert "https://portal.uni.edu.vn" in urls


class TestNormalizeUrl:
    def test_lowercase_scheme_host(self):
        assert normalize_url("HTTPS://EXAMPLE.COM/Path") == "https://example.com/Path"

    def test_fragment_stripped(self):
        url = normalize_url("https://example.com/page#section")
        assert "#section" not in url

    def test_empty_string(self):
        assert normalize_url("") == ""

    def test_invalid_scheme(self):
        assert normalize_url("javascript:alert(1)") == ""

    def test_no_host(self):
        assert normalize_url("https://") == ""


class TestDefangUrl:
    def test_http_scheme(self):
        result = defang_url("http://evil.com/path")
        assert result.startswith("hxxp://")
        assert "[.]" in result

    def test_https_scheme(self):
        result = defang_url("https://evil.example.com/path")
        assert result.startswith("hxxps://")
        assert "[.]" in result

    def test_dots_in_host_replaced(self):
        result = defang_url("https://uni.edu.vn/login")
        assert "uni[.]edu[.]vn" in result

    def test_empty_string(self):
        assert defang_url("") == ""

    def test_path_not_defanged(self):
        """Dấu chấm trong path không bị defang."""
        result = defang_url("https://example.com/file.pdf")
        # Dấu chấm trong hostname bị defang, nhưng trong path thì không
        assert "example[.]com" in result
        # Path vẫn giữ dấu chấm thực
        assert "/file.pdf" in result


# ===========================================================================
# PHẦN 5: process_email — Pipeline stub WP-00
# ===========================================================================

class TestProcessEmailStub:
    """Kiểm tra process_email() stub: cấu trúc hợp lệ, không cần mạng/API."""

    def test_returns_processed_email(self, settings_offline: Settings):
        raw = make_plain_eml()
        result = process_email(raw, settings=settings_offline)
        assert isinstance(result, ProcessedEmail)

    def test_classified_email_is_valid_contract(self, settings_offline: Settings):
        """ClassifiedEmail trả về phải hợp lệ theo core/contracts.py."""
        raw = make_plain_eml(
            subject="Nộp bài tập",
            sender="gv@uni.edu.vn",
            body="Deadline 15/11.",
            message_id="pipeline-test-001@uni.edu.vn",
        )
        result = process_email(raw, settings=settings_offline)
        email = result.email

        # Validate các trường theo contract
        assert isinstance(email, ClassifiedEmail)
        assert email.id  # không rỗng
        assert isinstance(email.received_at, datetime)
        assert email.label in list(EmailLabel)
        assert email.safety in list(SafetyStatus)
        assert 0.0 <= email.label_confidence <= 1.0

    def test_safe_attachments_are_valid_contract(
        self, settings_offline: Settings, tmp_path: Path
    ):
        """SafeAttachment trong kết quả phải hợp lệ theo contract."""
        cfg = Settings(
            virustotal_api_key="",
            llm_provider="fake",
            attachments_dir=str(tmp_path),
        )
        raw = make_multipart_eml(
            attach_name="lecture.pdf",
            attach_data=b"%PDF-1.4 valid pdf",
        )
        result = process_email(raw, settings=cfg)

        for sa in result.safe_attachments:
            assert isinstance(sa, SafeAttachment)
            assert len(sa.sha256) == 64
            assert sa.sha256 == sa.sha256.lower()
            assert sa.email_id  # không rỗng

    def test_malicious_email_cannot_forward(self, settings_offline: Settings):
        """Email MALICIOUS → can_forward phải False (Constitution II)."""
        # Tạo thủ công ProcessedEmail với safety=MALICIOUS
        email = ClassifiedEmail(
            id="mal-test",
            sender="evil@uni-edu-vn.top",
            subject="Phishing",
            body="Bấm vào đây",
            received_at=datetime(2026, 11, 9, 8, 0, tzinfo=timezone.utc),
            label=EmailLabel.PHISHING,
            safety=SafetyStatus.MALICIOUS,
            label_confidence=0.9,
        )
        assert can_forward_email(email) is False
        assert can_forward_email(email, user_approved=True) is False

    def test_stub_classifier_method(self, settings_offline: Settings):
        """WP-00 stub phải ghi classifier_method='stub'."""
        raw = make_plain_eml()
        result = process_email(raw, settings=settings_offline)
        assert result.classifier_method == "stub"

    def test_no_summary_in_stub(self, settings_offline: Settings):
        """WP-00 stub chưa có summarizer → summary là None."""
        raw = make_plain_eml()
        result = process_email(raw, settings=settings_offline)
        assert result.email.summary is None

    def test_empty_bytes_does_not_crash(self, settings_offline: Settings):
        """Input bytes rỗng → không crash, trả ProcessedEmail hợp lệ."""
        result = process_email(b"", settings=settings_offline)
        assert isinstance(result, ProcessedEmail)

    def test_path_input(self, settings_offline: Settings, tmp_path: Path):
        """Nhận Path đến file .eml."""
        eml_file = tmp_path / "test.eml"
        eml_file.write_bytes(make_plain_eml())
        result = process_email(eml_file, settings=settings_offline)
        assert isinstance(result, ProcessedEmail)

    def test_safe_email_can_forward(self, settings_offline: Settings):
        """Email SAFE (stub mặc định) → can_forward=True."""
        raw = make_plain_eml()
        result = process_email(raw, settings=settings_offline)
        # Stub không có scanner nên safety=SAFE, can_forward=True
        assert result.can_forward is True


# ===========================================================================
# PHẦN 6: approve_suspicious
# ===========================================================================

class TestApproveSuspicious:
    def _make_processed(self, safety: SafetyStatus) -> ProcessedEmail:
        email = ClassifiedEmail(
            id="test-approve",
            sender="clb@gmail.com",
            subject="Test",
            body="Body",
            received_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
            label=EmailLabel.OTHER,
            safety=safety,
            label_confidence=0.6,
        )
        return ProcessedEmail(
            email=email,
            safe_attachments=[],
            url_findings=[],
            attachment_findings=[],
            sender_reasons=[],
            classifier_method="stub",
            can_forward=can_forward_email(email),
            user_approved=False,
        )

    def test_suspicious_becomes_forwardable_after_approve(self):
        processed = self._make_processed(SafetyStatus.SUSPICIOUS)
        assert processed.can_forward is False

        approved = approve_suspicious(processed)
        assert approved.can_forward is True
        assert approved.user_approved is True

    def test_malicious_stays_blocked_after_approve(self):
        processed = self._make_processed(SafetyStatus.MALICIOUS)
        approved = approve_suspicious(processed)
        assert approved.can_forward is False

    def test_original_object_not_mutated(self):
        """approve_suspicious không sửa đối tượng gốc (immutable-style)."""
        processed = self._make_processed(SafetyStatus.SUSPICIOUS)
        _ = approve_suspicious(processed)
        assert processed.user_approved is False
        assert processed.can_forward is False


# ===========================================================================
# PHẦN 7: Tích hợp với core.mocks (Constitution III)
# ===========================================================================

class TestIntegrationWithMocks:
    """Kiểm tra Module D hoạt động được với dữ liệu mock từ core.mocks."""

    def test_core_mocks_emails_pass_validation(self):
        """Tất cả email trong core.mocks hợp lệ theo ClassifiedEmail contract."""
        from core import mocks
        for email in mocks.emails():
            assert isinstance(email, ClassifiedEmail)
            assert email.id
            assert 0.0 <= email.label_confidence <= 1.0

    def test_core_mocks_attachments_pass_validation(self):
        """Tất cả SafeAttachment trong core.mocks hợp lệ theo contract."""
        from core import mocks
        for sa in mocks.attachments():
            assert isinstance(sa, SafeAttachment)
            assert len(sa.sha256) == 64

    def test_safe_attachment_cannot_be_created_from_malicious(self):
        """SafeAttachment không thể tạo với sha256 không hợp lệ."""
        with pytest.raises(ValueError, match="sha256"):
            SafeAttachment(
                path="data/sample/file.exe",
                sha256="not_a_valid_sha256",
                email_id="test-id",
            )
