"""tests/email_security/test_url_scanner.py

Kiểm thử tự động cho WP-06: Quét an toàn URL offline bằng luật Heuristic (url_scanner.py).

Các trường hợp:
- Tên miền trường đại học chính thức: SAFE.
- Dịch vụ rút gọn link (bit.ly, tinyurl...): SUSPICIOUS (URL_SHORTENER).
- Địa chỉ IP trực tiếp (IPv4 / IPv6): SUSPICIOUS (URL_IP_DIRECT).
- Tên miền giả mạo / lừa đảo (hust-edu-login, domain lạ có từ khóa nhạy cảm, lừa đảo qua @): MALICIOUS (URL_SPOOFING).
"""
from __future__ import annotations

import pytest

from core.contracts import SafetyStatus
from modules.email_security.url_scanner import scan_url, scan_urls


class TestUrlScannerGenuineDomains:
    """Kiểm tra các tên miền trường học chính thức phải nhận diện là SAFE."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://hust.edu.vn",
            "https://portal.hust.edu.vn/sinhvien/tkb",
            "https://vnu.edu.vn/home",
            "https://uet.vnu.edu.vn/hoc-phan",
            "https://ptit.edu.vn/tuyen-sinh",
            "https://neu.edu.vn/dao-tao",
            "https://fpt.edu.vn/campus",
            "https://uni.edu.vn/login",
            "http://courses.uet.vnu.edu.vn/course/view.php?id=123",
        ],
    )
    def test_genuine_university_links_are_safe(self, url: str):
        finding = scan_url(url)
        assert finding.status == SafetyStatus.SAFE
        assert len(finding.reasons) == 0
        assert finding.url == url
        assert finding.defanged != ""


class TestUrlScannerShorteners:
    """Kiểm tra dịch vụ rút gọn link phải được gán SUSPICIOUS (URL_SHORTENER)."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://bit.ly/onthi2026",
            "http://tinyurl.com/tai-lieu-ai",
            "https://t.co/abc123xyz",
            "https://gg.gg/baitoan-csdl",
            "https://cutt.ly/slide-bai-giang",
            "https://shorturl.at/dopX1",
        ],
    )
    def test_shortener_links_are_suspicious(self, url: str):
        finding = scan_url(url)
        assert finding.status == SafetyStatus.SUSPICIOUS
        assert any(r.code == "URL_SHORTENER" for r in finding.reasons)
        assert "rút gọn" in finding.reasons[0].message.lower()


class TestUrlScannerDirectIP:
    """Kiểm tra đường link trỏ thẳng đến IP phải gán SUSPICIOUS (URL_IP_DIRECT)."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://192.168.1.1/admin",
            "http://10.0.0.5:8080/portal",
            "http://127.0.0.1/test",
            "http://103.21.244.2/download",
            "http://[::1]:8000/index",
            "http://[2001:db8::1]/path",
        ],
    )
    def test_direct_ip_links_are_suspicious(self, url: str):
        finding = scan_url(url)
        assert finding.status == SafetyStatus.SUSPICIOUS
        assert any(r.code == "URL_IP_DIRECT" for r in finding.reasons)
        assert "ip" in finding.reasons[0].message.lower()


class TestUrlScannerSpoofingAndPhishing:
    """Kiểm tra các tên miền giả mạo / lừa đảo phải gán MALICIOUS (URL_SPOOFING)."""

    @pytest.mark.parametrize(
        "url",
        [
            # A: Nhái tên trường với tên miền giả mạo
            "http://hust-edu-login.com",
            "http://hust.edu.vn.evil.com/login",
            "http://vnu-edu-portal.top/check",
            "http://neu-edu-login.xyz",
            "http://fpt-edu-support.online",
            "http://uni-edu-vn.top/verify",
            # B: Từ khóa nhạy cảm trên TLD rủi ro
            "http://portal-sinhvien-verify.xyz",
            "http://xac-nhan-tai-khoan.click/verify?token=123",
            "http://doi-mat-khau-sinhvien.top",
            "http://nhan-hoc-bong-sinh-vien.xyz/claim",
            # C: Thủ đoạn userinfo lừa đảo: @evil.com
            "https://hust.edu.vn@evil.com/steal-password",
            "https://vnu.edu.vn:password@attacker.site/login",
        ],
    )
    def test_spoofing_and_phishing_links_are_malicious(self, url: str):
        finding = scan_url(url)
        assert finding.status == SafetyStatus.MALICIOUS
        assert any(r.code == "URL_SPOOFING" for r in finding.reasons)
        assert len(finding.reasons) > 0


class TestScanUrlsBatch:
    """Kiểm thử quét danh sách nhiều URL cùng lúc."""

    def test_scan_multiple_urls(self):
        urls = [
            "https://hust.edu.vn/news",
            "https://bit.ly/tailieu",
            "http://192.168.1.1/test",
            "http://hust-edu-login.com",
        ]
        findings = scan_urls(urls)
        assert len(findings) == 4

        assert findings[0].status == SafetyStatus.SAFE
        assert findings[1].status == SafetyStatus.SUSPICIOUS
        assert findings[2].status == SafetyStatus.SUSPICIOUS
        assert findings[3].status == SafetyStatus.MALICIOUS

    def test_scan_empty_urls_list(self):
        assert scan_urls([]) == []

    def test_empty_or_whitespace_url(self):
        finding = scan_url("   ")
        assert finding.status == SafetyStatus.SAFE
        assert finding.reasons == []
