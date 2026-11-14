"""tests/email_security/test_redact_summarizer.py

Kiểm thử tự động cho:
- WP-05a: Ẩn danh thông tin cá nhân (redact_pii)
- WP-05b: Tóm tắt email học tập (summarize_email)

100% Offline:
- Tự động chặn kết nối mạng (fixture autouse block_network trong conftest).
- Sử dụng Mock LLMClient để kiểm tra logic tóm tắt mà không cần API key hay internet.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.contracts import ClassifiedEmail, EmailLabel, SafetyStatus
from core.llm_client import LLMClient, LLMResponse, LLMNotConfigured
from modules.email_security.models import ProcessedEmail
from modules.email_security.redact import redact_pii
from modules.email_security.summarizer import (
    MALICIOUS_BLOCK_MESSAGE,
    summarize_email,
)


# ===========================================================================
# PHẦN 1: Kiểm thử WP-05a (Ẩn danh thông tin cá nhân PII)
# ===========================================================================

class TestRedactPII:
    """Kiểm tra hàm redact_pii() che email, SĐT, MSSV."""

    def test_redact_email_simple(self):
        text = "Vui lòng liên hệ nguyen.van.a@hust.edu.vn để biết thêm chi tiết."
        result = redact_pii(text)
        assert "[EMAIL]" in result
        assert "nguyen.van.a@hust.edu.vn" not in result

    def test_redact_multiple_emails(self):
        text = "Gửi bài qua teacher@vnu.edu.vn hoặc cc assistant123@gmail.com."
        result = redact_pii(text)
        assert result.count("[EMAIL]") == 2
        assert "teacher@vnu.edu.vn" not in result
        assert "assistant123@gmail.com" not in result

    def test_redact_phone_vietnamese_standard(self):
        """Đầu số 03, 05, 07, 08, 09 (10 chữ số)."""
        samples = [
            "Gọi 0912345678 khi đến nơi.",
            "SĐT phụ huynh: 0381234567.",
            "Hotline: 0701234567.",
            "Tư vấn tuyển sinh: 0521234567.",
            "Phòng CTSV: 0811234567.",
        ]
        for s in samples:
            res = redact_pii(s)
            assert "[PHONE]" in res, f"Thất bại với: {s}"

    def test_redact_phone_with_dots_dashes_spaces(self):
        text = "Liên hệ 0912.345.678 hoặc 090-123-4567 hoặc 098 765 4321."
        result = redact_pii(text)
        assert result.count("[PHONE]") == 3
        assert "0912" not in result

    def test_redact_phone_with_country_code(self):
        text = "Số quốc tế: +84912345678 và (+84) 987 654 321."
        result = redact_pii(text)
        assert result.count("[PHONE]") == 2
        assert "+84" not in result

    def test_redact_student_id_8_digits_starting_20_to_24(self):
        """Dạng 20xxxxxx - 24xxxxxx (K65 - K69)."""
        samples = [
            ("Sinh viên MSSV: 20210123 nộp báo cáo.", "20210123"),
            ("MSSV 22123456 có mặt.", "22123456"),
            ("Đại diện nhóm: 23110099.", "23110099"),
            ("Học viên 24129999.", "24129999"),
            ("Khóa cũ: 20181234.", "20181234"),
        ]
        for text, mssv in samples:
            res = redact_pii(text)
            assert "[STUDENT_ID]" in res, f"Không che được {mssv} trong: {text}"
            assert mssv not in res

    def test_redact_student_id_two_letters_six_digits(self):
        """Dạng 2 chữ cái + 6 số (ví dụ B21DCCN... hoặc CT040123, AT160123)."""
        samples = [
            ("Mã số CT040123 xin phép nghỉ học.", "CT040123"),
            ("Sinh viên AT160456 nộp đồ án.", "AT160456"),
            ("MSSV: dt201234.", "dt201234"),
        ]
        for text, mssv in samples:
            res = redact_pii(text)
            assert "[STUDENT_ID]" in res, f"Không che được {mssv} trong: {text}"
            assert mssv not in res

    def test_do_not_redact_normal_years_and_short_numbers(self):
        text = "Năm học 2026 - 2027 có 120 sinh viên đạt loại A."
        result = redact_pii(text)
        assert "2026" in result
        assert "2027" in result
        assert "120" in result
        assert "[STUDENT_ID]" not in result

    def test_combined_pii(self):
        """Kết hợp cả email, SĐT và MSSV trong một thông báo."""
        text = (
            "Sinh viên Trần Văn B (MSSV: 20224567, SĐT: 0912.345.678) "
            "vui lòng gửi minh chứng về email phongdaotao@uni.edu.vn trước 17h."
        )
        res = redact_pii(text)
        assert "[STUDENT_ID]" in res
        assert "[PHONE]" in res
        assert "[EMAIL]" in res
        assert "20224567" not in res
        assert "0912.345.678" not in res
        assert "phongdaotao@uni.edu.vn" not in res

    def test_empty_string(self):
        assert redact_pii("") == ""
        assert redact_pii(None) == ""  # type: ignore[arg-type]


# ===========================================================================
# PHẦN 2: Kiểm thử WP-05b (Tóm tắt email học tập bằng LLM)
# ===========================================================================

def make_mock_llm(summary_text: str = "Tóm tắt mẫu.") -> LLMClient:
    """Tạo client LLM giả lập trả về tóm tắt định trước."""
    client = MagicMock(spec=LLMClient)
    client.is_configured.return_value = True
    client.generate.return_value = LLMResponse(
        text=summary_text,
        input_tokens=25,
        output_tokens=30,
        cached=False,
    )
    return client


class TestSummarizer:
    """Kiểm thử hàm summarize_email()."""

    def test_malicious_email_is_blocked_strictly(self):
        """Nguyên tắc Chặn tại cổng: email MALICIOUS không bao giờ gọi LLM."""
        mock_client = make_mock_llm()
        result = summarize_email(
            subject="Nhận học bổng khủng",
            body="Bấm vào link http://evil.com để nhận thưởng.",
            label=EmailLabel.PHISHING,
            safety_status=SafetyStatus.MALICIOUS,
            client=mock_client,
        )
        assert result == MALICIOUS_BLOCK_MESSAGE
        mock_client.generate.assert_not_called()

    def test_non_study_label_returns_empty_string(self):
        """Chỉ tóm tắt email học tập; SPAM / OTHER trả về chuỗi rỗng."""
        mock_client = make_mock_llm()
        for non_study in [EmailLabel.OTHER, EmailLabel.SPAM, EmailLabel.PHISHING]:
            result = summarize_email(
                subject="Tiêu đề linh tinh",
                body="Nội dung không liên quan đến học tập.",
                label=non_study,
                safety_status=SafetyStatus.SAFE,
                client=mock_client,
            )
            assert result == ""
        mock_client.generate.assert_not_called()

    def test_summarize_coursework_success(self):
        """Email bài tập (COURSEWORK / ASSIGNMENT) + SAFE -> tóm tắt thành công."""
        expected = "Nộp bài tập lớn giữa kỳ AI trước 23h59 thứ Sáu tuần sau."
        mock_client = make_mock_llm(expected)

        result = summarize_email(
            subject="[AI] Đề bài tập lớn giữa kỳ",
            body="Các nhóm nộp báo cáo SP1 trước 23h59 thứ Sáu tuần sau. Sinh viên 20211234 nộp.",
            label=EmailLabel.ASSIGNMENT,
            safety_status=SafetyStatus.SAFE,
            client=mock_client,
        )
        assert result == expected
        mock_client.generate.assert_called_once()

        # Kiểm tra nội dung gửi sang LLM đã được che PII
        call_prompt = mock_client.generate.call_args[0][0]
        assert "[STUDENT_ID]" in call_prompt
        assert "20211234" not in call_prompt

    def test_summarize_announcement_success(self):
        """Email thông báo chung (ANNOUNCEMENT) + SAFE -> tóm tắt thành công."""
        expected = "Lớp CSDL chiều thứ 4 chuyển sang phòng B203."
        mock_client = make_mock_llm(expected)

        result = summarize_email(
            subject="Thông báo đổi phòng học",
            body="Lớp CSDL chiều thứ Tư chuyển sang phòng B203.",
            label=EmailLabel.ANNOUNCEMENT,
            safety_status=SafetyStatus.SAFE,
            client=mock_client,
        )
        assert result == expected
        mock_client.generate.assert_called_once()

    def test_summarize_with_email_label_coursework_alias(self):
        """Kiểm tra gọi với nhãn EmailLabel.COURSEWORK (alias của ASSIGNMENT)."""
        mock_client = make_mock_llm("Hạn nộp lab mạng là chủ nhật.")
        result = summarize_email(
            subject="Lab 4 Mạng máy tính",
            body="Hạn nộp lab 4 là chủ nhật tuần này.",
            label=EmailLabel.COURSEWORK,
            safety_status=SafetyStatus.SAFE,
            client=mock_client,
        )
        assert result == "Hạn nộp lab mạng là chủ nhật."

    def test_offline_fallback_on_network_or_api_error(self):
        """Khi mất mạng / lỗi API -> tự động fallback trích 2 câu đầu tiên sau khi redact."""
        error_client = MagicMock(spec=LLMClient)
        error_client.generate.side_effect = ConnectionRefusedError("Mạng bị chặn hoàn toàn.")

        body = (
            "Lớp Trí tuệ nhân tạo nộp bài tập giữa kỳ vào thứ Hai. "
            "Liên hệ giáo viên qua email gv@uni.edu.vn hoặc SĐT 0987654321. "
            "Câu thứ ba không nên xuất hiện trong fallback."
        )

        result = summarize_email(
            subject="[AI] Nhắc nhở hạn nộp",
            body=body,
            label=EmailLabel.ASSIGNMENT,
            safety_status=SafetyStatus.SAFE,
            client=error_client,
        )

        assert "[EMAIL]" in result
        assert "[PHONE]" in result
        assert "gv@uni.edu.vn" not in result
        assert "0987654321" not in result
        assert "Câu thứ ba" not in result
        assert len(result) <= 150

    def test_summary_length_limit_150_chars(self):
        """Kết quả tóm tắt từ LLM nếu quá dài sẽ được cắt gọn <= 150 ký tự."""
        long_summary = (
            "Đây là một bản tóm tắt siêu dài do mô hình sinh ra vượt quá giới hạn 150 ký tự "
            "quy định trong tài liệu thiết kế. Hệ thống cần tự động cắt bớt và thêm dấu chấm lửng "
            "để đảm bảo không làm vỡ giao diện người dùng trên Streamlit."
        )
        mock_client = make_mock_llm(long_summary)

        result = summarize_email(
            subject="Đồ án",
            body="Chi tiết đồ án.",
            label=EmailLabel.ASSIGNMENT,
            safety_status=SafetyStatus.SAFE,
            client=mock_client,
        )
        assert len(result) <= 150
        assert result.endswith("...")

    def test_summarize_accepts_classified_email_object(self):
        """Hỗ trợ truyền thẳng đối tượng ClassifiedEmail."""
        mock_client = make_mock_llm("Tóm tắt từ ClassifiedEmail.")
        from datetime import datetime, timezone
        email = ClassifiedEmail(
            id="e-test-1",
            sender="gv@uni.edu.vn",
            subject="Thông báo học kỳ mới",
            body="Học kỳ 2 bắt đầu từ ngày 15/01/2027.",
            received_at=datetime(2026, 11, 15, tzinfo=timezone.utc),
            label=EmailLabel.ANNOUNCEMENT,
            safety=SafetyStatus.SAFE,
        )
        result = summarize_email(email, client=mock_client)
        assert result == "Tóm tắt từ ClassifiedEmail."
