"""tests/email_security/test_virustotal.py

Unit tests cho WP-07 — virustotal.py.
Tất cả các lệnh gọi VirusTotal API đều được mock bằng unittest.mock.patch
để chạy 100% offline (tuân thủ block_network fixture trong conftest.py).
"""

from __future__ import annotations

import base64
import io
import json
import time
import urllib.error
from unittest.mock import MagicMock, patch

from core.contracts import SafeAttachment, SafetyStatus
from modules.email_security.attachment_scanner import AttachmentScanResult
from modules.email_security.models import AttachmentFinding, Reason, UrlFinding
from modules.email_security.virustotal import (
    RateLimiter,
    VirusTotalCache,
    VirusTotalClient,
    lookup_file_hash,
    lookup_url_reputation,
    map_vt_stats_to_status,
    verify_attachment_with_vt,
    verify_url_with_vt,
)

FAKE_API_KEY = "test_virustotal_api_key_1234567890abcdef"
TEST_URL = "https://example-phishing-test.com/login"
TEST_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def _mock_vt_response(
    malicious: int = 0,
    suspicious: int = 0,
    harmless: int = 70,
    undetected: int = 5,
) -> MagicMock:
    """Tạo mock response trả về từ urllib.request.urlopen."""
    payload = {
        "data": {
            "attributes": {
                "last_analysis_stats": {
                    "malicious": malicious,
                    "suspicious": suspicious,
                    "harmless": harmless,
                    "undetected": undetected,
                }
            }
        }
    }
    body = json.dumps(payload).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None
    return mock_resp


# ===========================================================================
# NHÓM 1 — Quy đổi thống kê (map_vt_stats_to_status)
# ===========================================================================


class TestStatsMapping:
    """Quy đổi số lượng engine phát hiện sang SafetyStatus theo yêu cầu đề bài:

    - malicious >= 2 -> MALICIOUS
    - malicious == 1 or suspicious >= 1 -> SUSPICIOUS
    - ngược lại -> SAFE
    """

    def test_clean_is_safe(self) -> None:
        assert map_vt_stats_to_status(malicious=0, suspicious=0) == SafetyStatus.SAFE

    def test_one_suspicious_is_suspicious(self) -> None:
        assert (
            map_vt_stats_to_status(malicious=0, suspicious=1) == SafetyStatus.SUSPICIOUS
        )

    def test_multiple_suspicious_is_suspicious(self) -> None:
        assert (
            map_vt_stats_to_status(malicious=0, suspicious=5) == SafetyStatus.SUSPICIOUS
        )

    def test_one_malicious_is_suspicious(self) -> None:
        assert (
            map_vt_stats_to_status(malicious=1, suspicious=0) == SafetyStatus.SUSPICIOUS
        )

    def test_one_malicious_and_suspicious_is_suspicious(self) -> None:
        assert (
            map_vt_stats_to_status(malicious=1, suspicious=2) == SafetyStatus.SUSPICIOUS
        )

    def test_two_malicious_is_malicious(self) -> None:
        assert (
            map_vt_stats_to_status(malicious=2, suspicious=0) == SafetyStatus.MALICIOUS
        )

    def test_many_malicious_is_malicious(self) -> None:
        assert (
            map_vt_stats_to_status(malicious=10, suspicious=5) == SafetyStatus.MALICIOUS
        )


# ===========================================================================
# NHÓM 2 — API Key & Fallback khi thiếu Key
# ===========================================================================


class TestApiKeyManagement:
    """Xử lý API key: không crash khi thiếu key, fallback an toàn."""

    def test_no_api_key_returns_no_key_error(self) -> None:
        """Khi API key rỗng, hàm trả về status=None và error='no_key'."""
        cache = VirusTotalCache(":memory:")
        rep = lookup_url_reputation(
            TEST_URL, api_key="", cache=cache, enable_rate_limit=False
        )
        assert rep.status is None
        assert rep.error == "no_key"

    def test_no_api_key_file_hash_returns_no_key_error(self) -> None:
        """Tra cứu mã băm khi thiếu API key trả về error='no_key'."""
        cache = VirusTotalCache(":memory:")
        rep = lookup_file_hash(
            TEST_SHA256, api_key="", cache=cache, enable_rate_limit=False
        )
        assert rep.status is None
        assert rep.error == "no_key"

    def test_verify_url_fallback_when_no_key(self) -> None:
        """verify_url_with_vt giữ nguyên trạng thái SUSPICIOUS và bổ sung lý do khi thiếu key."""
        cache = VirusTotalCache(":memory:")
        finding = UrlFinding(
            url=TEST_URL,
            defanged="hxxp://test",
            status=SafetyStatus.SUSPICIOUS,
            reasons=[Reason(code="URL_SHORTENER", message="Rút gọn link")],
        )

        result = verify_url_with_vt(
            finding, api_key="", cache=cache, enable_rate_limit=False
        )
        assert result.status == SafetyStatus.SUSPICIOUS
        assert any(r.code == "VT_NO_KEY" for r in result.reasons)

    def test_verify_attachment_fallback_when_no_key(self) -> None:
        """verify_attachment_with_vt giữ nguyên SUSPICIOUS khi thiếu key."""
        cache = VirusTotalCache(":memory:")
        scan_res = AttachmentScanResult(
            filename="document.zip",
            file_path="data/real/e1/document.zip",
            sha256=TEST_SHA256,
            status=SafetyStatus.SUSPICIOUS,
            reasons=["Định dạng nén"],
        )

        result = verify_attachment_with_vt(
            scan_res, api_key="", cache=cache, enable_rate_limit=False
        )
        assert result.status == SafetyStatus.SUSPICIOUS
        assert any("API key" in r for r in result.reasons)


# ===========================================================================
# NHÓM 3 — Tra cứu URL Reputation (lookup_url_reputation)
# ===========================================================================


class TestUrlReputation:
    """Kiểm tra logic tra cứu URL qua VirusTotal v3."""

    def test_url_id_encoding_format(self) -> None:
        """Đặc tả VT v3: url_id = base64.urlsafe_b64encode(url.encode()).decode().strip('=')."""
        url = "https://example.com/test?a=1&b=2"
        expected_id = (
            base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii").strip("=")
        )

        cache = VirusTotalCache(":memory:")
        with patch(
            "urllib.request.urlopen", return_value=_mock_vt_response(0, 0, 70)
        ) as mock_open:
            lookup_url_reputation(
                url, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert mock_open.called
            req = mock_open.call_args[0][0]
            assert expected_id in req.full_url
            assert req.headers["X-apikey"] == FAKE_API_KEY

    def test_clean_url_safe(self) -> None:
        """URL sạch (0 malicious, 0 suspicious, 70 harmless) -> SAFE."""
        cache = VirusTotalCache(":memory:")
        with patch("urllib.request.urlopen", return_value=_mock_vt_response(0, 0, 70)):
            rep = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert rep.status == SafetyStatus.SAFE
            assert rep.malicious == 0
            assert rep.suspicious == 0
            assert rep.harmless == 70
            assert rep.error is None

    def test_suspicious_url_due_to_suspicious_engine(self) -> None:
        """URL có 1 engine suspicious -> SUSPICIOUS."""
        cache = VirusTotalCache(":memory:")
        with patch("urllib.request.urlopen", return_value=_mock_vt_response(0, 1, 60)):
            rep = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert rep.status == SafetyStatus.SUSPICIOUS
            assert rep.malicious == 0
            assert rep.suspicious == 1

    def test_suspicious_url_due_to_single_malicious_engine(self) -> None:
        """URL có 1 engine malicious -> SUSPICIOUS (chưa đủ 2 để coi là MALICIOUS)."""
        cache = VirusTotalCache(":memory:")
        with patch("urllib.request.urlopen", return_value=_mock_vt_response(1, 0, 60)):
            rep = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert rep.status == SafetyStatus.SUSPICIOUS
            assert rep.malicious == 1

    def test_malicious_url_two_engines(self) -> None:
        """URL có >= 2 engine malicious -> MALICIOUS."""
        cache = VirusTotalCache(":memory:")
        with patch("urllib.request.urlopen", return_value=_mock_vt_response(2, 0, 50)):
            rep = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert rep.status == SafetyStatus.MALICIOUS
            assert rep.malicious == 2

    def test_malicious_url_many_engines(self) -> None:
        """URL có nhiều engine malicious -> MALICIOUS."""
        cache = VirusTotalCache(":memory:")
        with patch("urllib.request.urlopen", return_value=_mock_vt_response(15, 3, 20)):
            rep = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert rep.status == SafetyStatus.MALICIOUS
            assert rep.malicious == 15

    def test_unpacking_support(self) -> None:
        """Hỗ trợ unpacking tuple: status, rep = lookup_url_reputation(...)."""
        cache = VirusTotalCache(":memory:")
        with patch("urllib.request.urlopen", return_value=_mock_vt_response(0, 0, 70)):
            status, rep = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert status == SafetyStatus.SAFE
            assert rep.harmless == 70

    def test_empty_url_returns_not_found(self) -> None:
        """URL rỗng không gọi mạng, trả về not_found."""
        cache = VirusTotalCache(":memory:")
        rep = lookup_url_reputation(
            "", api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
        )
        assert rep.status is None
        assert rep.error == "not_found"


# ===========================================================================
# NHÓM 4 — Tra cứu File Hash (lookup_file_hash)
# ===========================================================================


class TestFileHashReputation:
    """Kiểm tra logic tra cứu mã băm SHA-256."""

    def test_sha256_endpoint_called(self) -> None:
        """Tra cứu SHA-256 gọi đúng endpoint /api/v3/files/{sha256}."""
        cache = VirusTotalCache(":memory:")
        with patch(
            "urllib.request.urlopen", return_value=_mock_vt_response(0, 0, 65)
        ) as mock_open:
            lookup_file_hash(
                TEST_SHA256, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            req = mock_open.call_args[0][0]
            assert f"/api/v3/files/{TEST_SHA256}" in req.full_url

    def test_sha256_uppercase_normalized(self) -> None:
        """Mã băm chữ hoa được tự động chuẩn hóa về chữ thường."""
        cache = VirusTotalCache(":memory:")
        with patch(
            "urllib.request.urlopen", return_value=_mock_vt_response(0, 0, 65)
        ) as mock_open:
            lookup_file_hash(
                TEST_SHA256.upper(),
                api_key=FAKE_API_KEY,
                cache=cache,
                enable_rate_limit=False,
            )
            req = mock_open.call_args[0][0]
            assert f"/api/v3/files/{TEST_SHA256.lower()}" in req.full_url

    def test_clean_file_safe(self) -> None:
        """Mã băm sạch -> SAFE."""
        cache = VirusTotalCache(":memory:")
        with patch("urllib.request.urlopen", return_value=_mock_vt_response(0, 0, 65)):
            rep = lookup_file_hash(
                TEST_SHA256, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert rep.status == SafetyStatus.SAFE
            assert rep.malicious == 0

    def test_malicious_file_two_engines(self) -> None:
        """Mã băm có >= 2 engine malicious -> MALICIOUS."""
        cache = VirusTotalCache(":memory:")
        with patch("urllib.request.urlopen", return_value=_mock_vt_response(3, 1, 40)):
            rep = lookup_file_hash(
                TEST_SHA256, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert rep.status == SafetyStatus.MALICIOUS
            assert rep.malicious == 3

    def test_empty_sha256_returns_not_found(self) -> None:
        """SHA-256 rỗng không gọi mạng, trả về not_found."""
        cache = VirusTotalCache(":memory:")
        rep = lookup_file_hash(
            "", api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
        )
        assert rep.status is None
        assert rep.error == "not_found"


# ===========================================================================
# NHÓM 5 — Xử lý lỗi HTTP & Mạng
# ===========================================================================


class TestHttpAndNetworkErrors:
    """Xử lý các mã lỗi HTTP (404, 429, 401, 500) và lỗi mạng."""

    def test_http_404_not_found(self) -> None:
        """HTTP 404 (Resource chưa có trên VT) -> status=None, error='not_found'."""
        cache = VirusTotalCache(":memory:")
        err = urllib.error.HTTPError(
            url="https://virustotal.com",
            code=404,
            msg="Not Found",
            hdrs={},  # type: ignore
            fp=io.BytesIO(b"{}"),
        )
        with patch("urllib.request.urlopen", side_effect=err):
            rep = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert rep.status is None
            assert rep.error == "not_found"

    def test_http_429_rate_limited(self) -> None:
        """HTTP 429 (Vượt quá hạn mức / Quota Exceeded) -> status=None, error='rate_limited'."""
        cache = VirusTotalCache(":memory:")
        err = urllib.error.HTTPError(
            url="https://virustotal.com",
            code=429,
            msg="Rate limit exceeded",
            hdrs={},  # type: ignore
            fp=io.BytesIO(b"{}"),
        )
        with patch("urllib.request.urlopen", side_effect=err):
            rep = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert rep.status is None
            assert rep.error == "rate_limited"

    def test_http_401_invalid_key(self) -> None:
        """HTTP 401 (Sai / thiếu quyền API Key) -> status=None, error='no_key'."""
        cache = VirusTotalCache(":memory:")
        err = urllib.error.HTTPError(
            url="https://virustotal.com",
            code=401,
            msg="Unauthorized",
            hdrs={},  # type: ignore
            fp=io.BytesIO(b"{}"),
        )
        with patch("urllib.request.urlopen", side_effect=err):
            rep = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert rep.status is None
            assert rep.error == "no_key"

    def test_network_urlerror(self) -> None:
        """Lỗi kết nối mạng (URLError) -> status=None, error='network'."""
        cache = VirusTotalCache(":memory:")
        err = urllib.error.URLError(reason="Connection timed out")
        with patch("urllib.request.urlopen", side_effect=err):
            rep = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert rep.status is None
            assert rep.error == "network"

    def test_invalid_json_response(self) -> None:
        """Phản hồi không phải JSON hợp lệ -> status=None, error='json_error'."""
        cache = VirusTotalCache(":memory:")
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"<!DOCTYPE html>Gateway Timeout"
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_resp):
            rep = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert rep.status is None
            assert rep.error == "json_error"


# ===========================================================================
# NHÓM 6 — Bộ nhớ đệm SQLite & TTL
# ===========================================================================


class TestSQLiteCache:
    """Bộ nhớ đệm SQLite: Cache hit, cache miss, TTL và lưu trữ dữ liệu."""

    def test_cache_hit_avoids_api_call(self) -> None:
        """Khi cache hit, không thực hiện gọi API lần thứ 2."""
        cache = VirusTotalCache(":memory:")

        # Lần 1: Gọi API (cache miss)
        with patch(
            "urllib.request.urlopen", return_value=_mock_vt_response(0, 0, 70)
        ) as mock_open:
            rep1 = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert mock_open.call_count == 1
            assert rep1.status == SafetyStatus.SAFE
            assert rep1.source == "virustotal"

        # Lần 2: Lấy từ cache (cache hit, mock_open không được gọi thêm)
        with patch("urllib.request.urlopen") as mock_open_2:
            rep2 = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert mock_open_2.call_count == 0
            assert rep2.status == SafetyStatus.SAFE
            assert rep2.source == "virustotal_cache"
            assert rep2.harmless == 70

    def test_cache_ttl_expiration(self) -> None:
        """Khi bản ghi trong cache vượt quá TTL, cache coi như miss và gọi lại API."""
        ttl_short = 1  # 1 giây
        cache = VirusTotalCache(":memory:", ttl_seconds=ttl_short)

        # Lưu bản ghi giả có checked_at cũ hơn 2 giây
        old_time = time.time() - 2.0
        cache.set(
            "url",
            TEST_URL,
            malicious_count=0,
            suspicious_count=0,
            harmless_count=70,
            checked_at=old_time,
        )

        # Kiểm tra get trực tiếp thấy None vì đã hết TTL
        assert cache.get("url", TEST_URL) is None

        # Khi gọi lookup -> phải gọi API lại
        with patch(
            "urllib.request.urlopen", return_value=_mock_vt_response(2, 0, 50)
        ) as mock_open:
            rep = lookup_url_reputation(
                TEST_URL, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert mock_open.call_count == 1
            assert rep.status == SafetyStatus.MALICIOUS

    def test_cache_stores_both_url_and_sha256(self) -> None:
        """Cache lưu độc lập giữa resource_type='url' và 'sha256'."""
        cache = VirusTotalCache(":memory:")
        cache.set(
            "url",
            "https://site.com",
            malicious_count=0,
            suspicious_count=0,
            harmless_count=50,
        )
        cache.set(
            "sha256",
            "abc123sha",
            malicious_count=5,
            suspicious_count=2,
            harmless_count=10,
        )

        url_entry = cache.get("url", "https://site.com")
        sha_entry = cache.get("sha256", "abc123sha")

        assert url_entry is not None
        assert url_entry["harmless_count"] == 50
        assert sha_entry is not None
        assert sha_entry["malicious_count"] == 5

    def test_cache_update_on_conflict(self) -> None:
        """Ghi đè bản ghi trùng khóa cập nhật các giá trị mới."""
        cache = VirusTotalCache(":memory:")
        cache.set(
            "url",
            "https://site.com",
            malicious_count=0,
            suspicious_count=0,
            harmless_count=50,
        )
        cache.set(
            "url",
            "https://site.com",
            malicious_count=3,
            suspicious_count=1,
            harmless_count=40,
        )

        entry = cache.get("url", "https://site.com")
        assert entry is not None
        assert entry["malicious_count"] == 3

    def test_cache_close_safe(self) -> None:
        """Đóng cache an toàn không phát sinh lỗi."""
        cache = VirusTotalCache(":memory:")
        cache.close()
        # Gọi close lần 2 không lỗi
        cache.close()


# ===========================================================================
# NHÓM 7 — Bộ điều tiết tần suất gọi (RateLimiter)
# ===========================================================================


class TestRateLimiter:
    """Kiểm tra giới hạn 4 request/phút của RateLimiter."""

    def test_rate_limiter_disabled(self) -> None:
        """Khi disabled, không bao giờ delay."""
        limiter = RateLimiter(max_requests=4, period_seconds=60.0, enabled=False)
        for _ in range(10):
            slept = limiter.acquire()
            assert slept == 0.0

    def test_rate_limiter_allows_up_to_max_requests(self) -> None:
        """Cho phép tối đa 4 request liên tiếp không bị delay."""
        limiter = RateLimiter(max_requests=4, period_seconds=60.0, enabled=True)
        for _ in range(4):
            slept = limiter.acquire()
            assert slept == 0.0

    def test_rate_limiter_delays_on_fifth_request(self) -> None:
        """Request thứ 5 trong chu kỳ phải chờ."""
        period = 0.05  # Chu kỳ ngắn để test
        limiter = RateLimiter(max_requests=2, period_seconds=period, enabled=True)
        assert limiter.acquire() == 0.0
        assert limiter.acquire() == 0.0

        # Request thứ 3 phải sleep
        slept = limiter.acquire()
        assert slept > 0.0

    def test_rate_limiter_reset(self) -> None:
        """reset() xóa sạch lịch sử gọi."""
        limiter = RateLimiter(max_requests=2, period_seconds=60.0, enabled=True)
        limiter.acquire()
        limiter.acquire()
        assert len(limiter._timestamps) == 2

        limiter.reset()
        assert len(limiter._timestamps) == 0


# ===========================================================================
# NHÓM 8 — Heuristic chạy trước, chỉ tra VT khi nghi ngờ (verify_url_with_vt)
# ===========================================================================


class TestVerifyUrlWithVT:
    """Xác thực URL qua VT: chỉ gọi khi SUSPICIOUS, bỏ qua khi SAFE hoặc MALICIOUS."""

    def test_safe_url_bypasses_vt(self) -> None:
        """URL đã SAFE từ heuristic -> KHÔNG gọi VirusTotal."""
        cache = VirusTotalCache(":memory:")
        finding = UrlFinding(
            url="https://hust.edu.vn",
            defanged="https://hust.edu.vn",
            status=SafetyStatus.SAFE,
            reasons=[],
        )

        with patch("urllib.request.urlopen") as mock_open:
            result = verify_url_with_vt(
                finding, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert mock_open.call_count == 0
            assert result.status == SafetyStatus.SAFE
            assert result.reputation is None

    def test_malicious_url_bypasses_vt(self) -> None:
        """URL đã MALICIOUS từ heuristic -> KHÔNG gọi VirusTotal."""
        cache = VirusTotalCache(":memory:")
        finding = UrlFinding(
            url="https://hust.edu.vn@evil.com",
            defanged="hxxp://hust.edu.vn@evil[.]com",
            status=SafetyStatus.MALICIOUS,
            reasons=[Reason(code="URL_SPOOFING", message="Giả mạo")],
        )

        with patch("urllib.request.urlopen") as mock_open:
            result = verify_url_with_vt(
                finding, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert mock_open.call_count == 0
            assert result.status == SafetyStatus.MALICIOUS

    def test_suspicious_url_checked_and_becomes_malicious(self) -> None:
        """URL SUSPICIOUS -> gọi VT -> VT phát hiện mã độc -> chuyển sang MALICIOUS."""
        cache = VirusTotalCache(":memory:")
        finding = UrlFinding(
            url="https://tinyurl.com/something",
            defanged="hxxp://tinyurl[.]com/something",
            status=SafetyStatus.SUSPICIOUS,
            reasons=[Reason(code="URL_SHORTENER", message="Rút gọn")],
        )

        with patch("urllib.request.urlopen", return_value=_mock_vt_response(4, 1, 10)):
            result = verify_url_with_vt(
                finding, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert result.status == SafetyStatus.MALICIOUS
            assert any(r.code == "VT_MALICIOUS" for r in result.reasons)
            assert result.reputation is not None
            assert result.reputation.malicious == 4

    def test_suspicious_url_checked_and_becomes_safe(self) -> None:
        """URL SUSPICIOUS -> gọi VT -> VT xác nhận sạch -> nâng lên SAFE."""
        cache = VirusTotalCache(":memory:")
        finding = UrlFinding(
            url="https://tinyurl.com/clean-link",
            defanged="hxxp://tinyurl[.]com/clean-link",
            status=SafetyStatus.SUSPICIOUS,
            reasons=[Reason(code="URL_SHORTENER", message="Rút gọn")],
        )

        with patch("urllib.request.urlopen", return_value=_mock_vt_response(0, 0, 75)):
            result = verify_url_with_vt(
                finding, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert result.status == SafetyStatus.SAFE
            assert any(r.code == "VT_CLEAN" for r in result.reasons)

    def test_force_vt_on_safe_url(self) -> None:
        """Khi bật force_vt=True, URL SAFE vẫn được kiểm tra qua VT."""
        cache = VirusTotalCache(":memory:")
        finding = UrlFinding(
            url="https://example.com",
            defanged="hxxp://example[.]com",
            status=SafetyStatus.SAFE,
            reasons=[],
        )

        with patch(
            "urllib.request.urlopen", return_value=_mock_vt_response(0, 0, 80)
        ) as mock_open:
            result = verify_url_with_vt(
                finding,
                api_key=FAKE_API_KEY,
                cache=cache,
                enable_rate_limit=False,
                force_vt=True,
            )
            assert mock_open.call_count == 1
            assert result.reputation is not None


# ===========================================================================
# NHÓM 9 — Heuristic chạy trước, chỉ tra VT khi nghi ngờ (verify_attachment_with_vt)
# ===========================================================================


class TestVerifyAttachmentWithVT:
    """Xác thực File đính kèm qua VT và nguyên tắc 'Chặn tại cổng'."""

    def test_safe_attachment_bypasses_vt(self) -> None:
        """File đã SAFE từ heuristic -> KHÔNG gọi VirusTotal."""
        cache = VirusTotalCache(":memory:")
        scan_res = AttachmentScanResult(
            filename="baitap.pdf",
            file_path="data/real/e1/baitap.pdf",
            sha256=TEST_SHA256,
            status=SafetyStatus.SAFE,
            reasons=[],
            safe_attachment=SafeAttachment(
                "data/real/e1/baitap.pdf", TEST_SHA256, "e1"
            ),
        )

        with patch("urllib.request.urlopen") as mock_open:
            result = verify_attachment_with_vt(
                scan_res, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert mock_open.call_count == 0
            assert result.status == SafetyStatus.SAFE
            assert result.safe_attachment is not None

    def test_malicious_attachment_bypasses_vt(self) -> None:
        """File đã MALICIOUS từ heuristic -> KHÔNG gọi VirusTotal."""
        cache = VirusTotalCache(":memory:")
        scan_res = AttachmentScanResult(
            filename="virus.exe",
            file_path="data/real/e1/virus.exe",
            sha256=TEST_SHA256,
            status=SafetyStatus.MALICIOUS,
            reasons=["Đuôi thực thi"],
            safe_attachment=None,
        )

        with patch("urllib.request.urlopen") as mock_open:
            result = verify_attachment_with_vt(
                scan_res, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert mock_open.call_count == 0
            assert result.status == SafetyStatus.MALICIOUS

    def test_suspicious_attachment_becomes_malicious_blocks_gate(self) -> None:
        """File SUSPICIOUS -> VT phát hiện độc hại -> MALICIOUS, safe_attachment bắt buộc là None."""
        cache = VirusTotalCache(":memory:")
        scan_res = AttachmentScanResult(
            filename="macro_file.docm",
            file_path="data/real/e1/macro_file.docm",
            sha256=TEST_SHA256,
            status=SafetyStatus.SUSPICIOUS,
            reasons=["Chứa macro"],
            safe_attachment=None,
        )

        with patch("urllib.request.urlopen", return_value=_mock_vt_response(5, 1, 10)):
            result = verify_attachment_with_vt(
                scan_res, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert result.status == SafetyStatus.MALICIOUS
            assert result.safe_attachment is None  # Nguyên tắc Chặn tại cổng!
            assert any("VirusTotal phát hiện mã độc" in r for r in result.reasons)

    def test_suspicious_attachment_becomes_safe_creates_safe_attachment(self) -> None:
        """File SUSPICIOUS -> VT xác nhận sạch -> SAFE, tự động tạo SafeAttachment nếu có email_id."""
        cache = VirusTotalCache(":memory:")
        scan_res = AttachmentScanResult(
            filename="archive.zip",
            file_path="data/real/e1/archive.zip",
            sha256=TEST_SHA256,
            status=SafetyStatus.SUSPICIOUS,
            reasons=["Định dạng nén"],
            safe_attachment=None,
        )

        with patch("urllib.request.urlopen", return_value=_mock_vt_response(0, 0, 70)):
            result = verify_attachment_with_vt(
                scan_res,
                api_key=FAKE_API_KEY,
                cache=cache,
                enable_rate_limit=False,
                email_id="email-001",
            )
            assert result.status == SafetyStatus.SAFE
            assert result.safe_attachment is not None
            assert isinstance(result.safe_attachment, SafeAttachment)
            assert result.safe_attachment.email_id == "email-001"
            assert result.safe_attachment.sha256 == TEST_SHA256

    def test_suspicious_attachment_with_finding_model(self) -> None:
        """verify_attachment_with_vt cũng hỗ trợ AttachmentFinding (models.py)."""
        cache = VirusTotalCache(":memory:")
        finding = AttachmentFinding(
            filename="notes.zip",
            path="data/real/e1/notes.zip",
            sha256=TEST_SHA256,
            size=1024,
            status=SafetyStatus.SUSPICIOUS,
            reasons=[Reason(code="SUSPICIOUS_EXT", message="Định dạng nén")],
        )

        with patch("urllib.request.urlopen", return_value=_mock_vt_response(0, 0, 68)):
            result = verify_attachment_with_vt(
                finding, api_key=FAKE_API_KEY, cache=cache, enable_rate_limit=False
            )
            assert result.status == SafetyStatus.SAFE
            assert result.reputation is not None
            assert any(r.code == "VT_CLEAN" for r in result.reasons)


# ===========================================================================
# NHÓM 10 — Client VirusTotal tổng hợp
# ===========================================================================


class TestVirusTotalClient:
    """Kiểm tra tổng hợp VirusTotalClient."""

    def test_client_init_defaults(self) -> None:
        """Khởi tạo client với các giá trị mặc định."""
        client = VirusTotalClient(
            api_key=FAKE_API_KEY,
            cache=VirusTotalCache(":memory:"),
            enable_rate_limit=False,
        )
        assert client.api_key == FAKE_API_KEY
        assert client.timeout == 10.0

    def test_client_lookup_url_and_file(self) -> None:
        """Client thực hiện cả 2 phương thức lookup_url và lookup_file."""
        client = VirusTotalClient(
            api_key=FAKE_API_KEY,
            cache=VirusTotalCache(":memory:"),
            enable_rate_limit=False,
        )
        with patch("urllib.request.urlopen", return_value=_mock_vt_response(0, 0, 60)):
            rep_url = client.lookup_url(TEST_URL)
            rep_file = client.lookup_file(TEST_SHA256)

            assert rep_url.status == SafetyStatus.SAFE
            assert rep_file.status == SafetyStatus.SAFE
