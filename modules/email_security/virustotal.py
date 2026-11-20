"""WP-07 — Tích hợp VirusTotal v3 API & Bộ nhớ đệm SQLite (plan_module_d.md § 6.2, § 6.3 & § WP-07).

Các tính năng chính:
  1. Quản lý API key: Đọc VIRUSTOTAL_API_KEY từ biến môi trường (.env / os.getenv).
     Nếu thiếu key -> không crash, tự động fallback về heuristic kèm ghi chú.
  2. Cache SQLite (mặc định data/vt_cache.sqlite hoặc :memory: khi test)
     tránh gọi lại API trùng lặp với TTL (mặc định 24h = 86400s).
  3. Rate Limiter: Giới hạn tối đa 4 request/phút (gói miễn phí của VirusTotal),
     có thể tắt delay khi chạy test (enable_rate_limit=False).
  4. Heuristic chạy trước, chỉ tra VirusTotal khi nghi ngờ (SafetyStatus.SUSPICIOUS).
  5. Quy đổi chỉ số phát hiện:
     - malicious >= 2 -> SafetyStatus.MALICIOUS
     - malicious == 1 hoặc suspicious >= 1 -> SafetyStatus.SUSPICIOUS
     - ngược lại -> SafetyStatus.SAFE
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.contracts import SafeAttachment, SafetyStatus
from .attachment_scanner import AttachmentScanResult
from .config import Settings
from .models import AttachmentFinding, Reason, Reputation, UrlFinding

logger = logging.getLogger(__name__)

# URL API VirusTotal v3
VT_URL_ENDPOINT = "https://www.virustotal.com/api/v3/urls/{url_id}"
VT_FILE_ENDPOINT = "https://www.virustotal.com/api/v3/files/{sha256}"

DEFAULT_CACHE_PATH = "data/vt_cache.sqlite"
DEFAULT_TTL_SECONDS = 86400  # 24 giờ


# ---------------------------------------------------------------------------
# Mô hình dữ liệu kết quả VirusTotal
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VTReputation(Reputation):
    """Kết quả tra cứu VirusTotal.

    Kế thừa models.Reputation (status, malicious, suspicious, source, error)
    và bổ sung trường harmless để lưu trữ số engine đánh giá an toàn.
    Hỗ trợ cả 2 cách dùng:
      1) rep = lookup_url_reputation(...) -> rep.status, rep.malicious...
      2) status, rep = lookup_url_reputation(...) -> unpacking tuple
    """

    harmless: int = 0

    def __iter__(self):
        yield self.status
        yield self


# ---------------------------------------------------------------------------
# Bộ nhớ đệm SQLite (vt_cache.sqlite)
# ---------------------------------------------------------------------------


class VirusTotalCache:
    """Bộ nhớ đệm SQLite cho kết quả tra cứu VirusTotal với hỗ trợ TTL.

    Lưu theo khóa (resource_type, resource_key) với:
      - resource_type: "url" hoặc "sha256"
      - resource_key: URL gốc hoặc mã SHA-256 (chữ thường)
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_CACHE_PATH,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ):
        self.db_path = str(db_path)
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()

        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        else:
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)

        self._init_db()

    def _init_db(self) -> None:
        """Tạo bảng vt_cache nếu chưa tồn tại."""
        with self._lock:
            with self._conn:
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vt_cache (
                        resource_type TEXT NOT NULL,
                        resource_key TEXT NOT NULL,
                        malicious_count INTEGER NOT NULL,
                        suspicious_count INTEGER NOT NULL,
                        harmless_count INTEGER NOT NULL,
                        checked_at REAL NOT NULL,
                        PRIMARY KEY (resource_type, resource_key)
                    )
                    """
                )

    def get(self, resource_type: str, resource_key: str) -> dict[str, Any] | None:
        """Lấy bản ghi từ cache nếu còn trong hạn TTL. Trả về None nếu không có hoặc đã hết hạn."""
        with self._lock:
            cursor = self._conn.execute(
                """
                SELECT malicious_count, suspicious_count, harmless_count, checked_at
                FROM vt_cache
                WHERE resource_type = ? AND resource_key = ?
                """,
                (resource_type, resource_key),
            )
            row = cursor.fetchone()
            if not row:
                return None

            malicious_count, suspicious_count, harmless_count, checked_at = row
            # Kiểm tra thời hạn sống của cache (TTL)
            if time.time() - checked_at > self.ttl_seconds:
                return None

            return {
                "resource_type": resource_type,
                "resource_key": resource_key,
                "malicious_count": malicious_count,
                "suspicious_count": suspicious_count,
                "harmless_count": harmless_count,
                "checked_at": checked_at,
            }

    def set(
        self,
        resource_type: str,
        resource_key: str,
        malicious_count: int,
        suspicious_count: int,
        harmless_count: int,
        checked_at: float | None = None,
    ) -> None:
        """Lưu hoặc cập nhật kết quả tra cứu vào cache."""
        if checked_at is None:
            checked_at = time.time()

        with self._lock:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO vt_cache (
                        resource_type, resource_key, malicious_count,
                        suspicious_count, harmless_count, checked_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(resource_type, resource_key) DO UPDATE SET
                        malicious_count = excluded.malicious_count,
                        suspicious_count = excluded.suspicious_count,
                        harmless_count = excluded.harmless_count,
                        checked_at = excluded.checked_at
                    """,
                    (
                        resource_type,
                        resource_key,
                        malicious_count,
                        suspicious_count,
                        harmless_count,
                        checked_at,
                    ),
                )

    def close(self) -> None:
        """Đóng kết nối cơ sở dữ liệu."""
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Bộ điều tiết tần suất gọi (Rate Limiter)
# ---------------------------------------------------------------------------


class RateLimiter:
    """Giới hạn tần suất gọi API VirusTotal (mặc định 4 request/phút cho gói miễn phí)."""

    def __init__(
        self,
        max_requests: int = 4,
        period_seconds: float = 60.0,
        enabled: bool = True,
    ):
        self.max_requests = max_requests
        self.period_seconds = period_seconds
        self.enabled = enabled
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> float:
        """Chờ nếu cần để không vượt quá giới hạn tần suất. Trả về thời gian đã đợi (giây)."""
        if not self.enabled or self.max_requests <= 0:
            return 0.0

        with self._lock:
            now = time.time()
            # Dọn dẹp các mốc thời gian ngoài chu kỳ quan sát
            self._timestamps = [
                t for t in self._timestamps if now - t < self.period_seconds
            ]

            slept = 0.0
            if len(self._timestamps) >= self.max_requests:
                oldest = self._timestamps[0]
                wait_time = self.period_seconds - (now - oldest)
                if wait_time > 0:
                    time.sleep(wait_time)
                    slept = wait_time
                now = time.time()
                self._timestamps = [
                    t for t in self._timestamps if now - t < self.period_seconds
                ]

            self._timestamps.append(time.time())
            return slept

    def reset(self) -> None:
        """Đặt lại lịch sử các lần gọi."""
        with self._lock:
            self._timestamps.clear()


# ---------------------------------------------------------------------------
# Hàm quy đổi số liệu thống kê sang SafetyStatus
# ---------------------------------------------------------------------------


def map_vt_stats_to_status(malicious: int, suspicious: int) -> SafetyStatus:
    """Quy đổi số lượng engine phát hiện sang SafetyStatus:

    * malicious >= 2 -> SafetyStatus.MALICIOUS
    * malicious == 1 hoặc suspicious >= 1 -> SafetyStatus.SUSPICIOUS
    * ngược lại -> SafetyStatus.SAFE
    """
    if malicious >= 2:
        return SafetyStatus.MALICIOUS
    if malicious == 1 or suspicious >= 1:
        return SafetyStatus.SUSPICIOUS
    return SafetyStatus.SAFE


# ---------------------------------------------------------------------------
# Client VirusTotal v3
# ---------------------------------------------------------------------------


class VirusTotalClient:
    """Client tương tác với VirusTotal API v3 có kèm cache SQLite và RateLimiter."""

    def __init__(
        self,
        api_key: str | None = None,
        cache: VirusTotalCache | None = None,
        db_path: str | Path = DEFAULT_CACHE_PATH,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        enable_rate_limit: bool = True,
        max_requests: int = 4,
        period_seconds: float = 60.0,
        timeout: float = 10.0,
    ):
        if api_key is not None:
            self.api_key = api_key.strip()
        else:
            self.api_key = os.getenv(
                "VIRUSTOTAL_API_KEY", Settings().virustotal_api_key
            ).strip()

        self.cache = cache or VirusTotalCache(db_path=db_path, ttl_seconds=ttl_seconds)
        self.rate_limiter = RateLimiter(
            max_requests=max_requests,
            period_seconds=period_seconds,
            enabled=enable_rate_limit,
        )
        self.timeout = timeout

    def lookup_url(self, url: str) -> VTReputation:
        """Tra cứu độ uy tín của một URL trên VirusTotal v3."""
        clean_url = (url or "").strip()
        if not clean_url:
            return VTReputation(
                status=None,
                malicious=0,
                suspicious=0,
                harmless=0,
                source="virustotal",
                error="not_found",
            )

        # 1. Kiểm tra cache
        cached = self.cache.get("url", clean_url)
        if cached is not None:
            m = cached["malicious_count"]
            s = cached["suspicious_count"]
            h = cached["harmless_count"]
            return VTReputation(
                status=map_vt_stats_to_status(m, s),
                malicious=m,
                suspicious=s,
                harmless=h,
                source="virustotal_cache",
                error=None,
            )

        # 2. Kiểm tra API key
        if not self.api_key:
            return VTReputation(
                status=None,
                malicious=0,
                suspicious=0,
                harmless=0,
                source="virustotal",
                error="no_key",
            )

        # 3. Chuẩn bị url_id theo đặc tả VirusTotal v3: base64.urlsafe_b64encode stripped "="
        url_bytes = clean_url.encode("utf-8")
        url_id = base64.urlsafe_b64encode(url_bytes).decode("ascii").strip("=")
        endpoint = VT_URL_ENDPOINT.format(url_id=url_id)

        # 4. Gọi API
        return self._request_and_cache("url", clean_url, endpoint)

    def lookup_file(self, sha256: str) -> VTReputation:
        """Tra cứu độ uy tín của mã băm SHA-256 trên VirusTotal v3."""
        clean_sha = (sha256 or "").strip().lower()
        if not clean_sha:
            return VTReputation(
                status=None,
                malicious=0,
                suspicious=0,
                harmless=0,
                source="virustotal",
                error="not_found",
            )

        # 1. Kiểm tra cache
        cached = self.cache.get("sha256", clean_sha)
        if cached is not None:
            m = cached["malicious_count"]
            s = cached["suspicious_count"]
            h = cached["harmless_count"]
            return VTReputation(
                status=map_vt_stats_to_status(m, s),
                malicious=m,
                suspicious=s,
                harmless=h,
                source="virustotal_cache",
                error=None,
            )

        # 2. Kiểm tra API key
        if not self.api_key:
            return VTReputation(
                status=None,
                malicious=0,
                suspicious=0,
                harmless=0,
                source="virustotal",
                error="no_key",
            )

        # 3. Chuẩn bị endpoint
        endpoint = VT_FILE_ENDPOINT.format(sha256=clean_sha)

        # 4. Gọi API
        return self._request_and_cache("sha256", clean_sha, endpoint)

    def _request_and_cache(
        self, resource_type: str, resource_key: str, endpoint: str
    ) -> VTReputation:
        """Thực hiện HTTP GET tới VirusTotal API v3, bắt lỗi và lưu cache nếu thành công."""
        self.rate_limiter.acquire()

        req = urllib.request.Request(
            endpoint,
            headers={
                "x-apikey": self.api_key,
                "Accept": "application/json",
                "User-Agent": "ai-study-assistant/1.0",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                payload = json.loads(body)

                stats = (
                    payload.get("data", {})
                    .get("attributes", {})
                    .get("last_analysis_stats", {})
                )
                m = int(stats.get("malicious", 0))
                s = int(stats.get("suspicious", 0))
                h = int(stats.get("harmless", 0))

                status = map_vt_stats_to_status(m, s)

                # Lưu cache kết quả hợp lệ
                self.cache.set(resource_type, resource_key, m, s, h)

                return VTReputation(
                    status=status,
                    malicious=m,
                    suspicious=s,
                    harmless=h,
                    source="virustotal",
                    error=None,
                )

        except urllib.error.HTTPError as exc:
            logger.warning("[VirusTotal] HTTPError %d for %s", exc.code, endpoint)
            if exc.code == 404:
                return VTReputation(
                    status=None,
                    malicious=0,
                    suspicious=0,
                    harmless=0,
                    source="virustotal",
                    error="not_found",
                )
            if exc.code == 429:
                return VTReputation(
                    status=None,
                    malicious=0,
                    suspicious=0,
                    harmless=0,
                    source="virustotal",
                    error="rate_limited",
                )
            if exc.code in (401, 403):
                return VTReputation(
                    status=None,
                    malicious=0,
                    suspicious=0,
                    harmless=0,
                    source="virustotal",
                    error="no_key",
                )
            return VTReputation(
                status=None,
                malicious=0,
                suspicious=0,
                harmless=0,
                source="virustotal",
                error=f"http_{exc.code}",
            )

        except urllib.error.URLError as exc:
            logger.warning("[VirusTotal] URLError for %s: %s", endpoint, exc)
            return VTReputation(
                status=None,
                malicious=0,
                suspicious=0,
                harmless=0,
                source="virustotal",
                error="network",
            )

        except json.JSONDecodeError:
            return VTReputation(
                status=None,
                malicious=0,
                suspicious=0,
                harmless=0,
                source="virustotal",
                error="json_error",
            )

        except Exception as exc:
            logger.warning("[VirusTotal] Unexpected error for %s: %s", endpoint, exc)
            return VTReputation(
                status=None,
                malicious=0,
                suspicious=0,
                harmless=0,
                source="virustotal",
                error="network",
            )


# ---------------------------------------------------------------------------
# Các hàm công khai theo yêu cầu đặc tả WP-07
# ---------------------------------------------------------------------------


def lookup_url_reputation(
    url: str,
    api_key: str | None = None,
    cache: VirusTotalCache | None = None,
    enable_rate_limit: bool = True,
    timeout: float = 10.0,
    client: VirusTotalClient | None = None,
) -> VTReputation:
    """Tra cứu thông tin danh tiếng của URL qua VirusTotal v3 API.

    Returns:
        VTReputation có thể đọc trực tiếp (rep.status, rep.malicious)
        hoặc giải nén dạng tuple (status, rep = lookup_url_reputation(...)).
    """
    if client is not None:
        return client.lookup_url(url)

    c = VirusTotalClient(
        api_key=api_key,
        cache=cache,
        enable_rate_limit=enable_rate_limit,
        timeout=timeout,
    )
    return c.lookup_url(url)


def lookup_file_hash(
    sha256: str,
    api_key: str | None = None,
    cache: VirusTotalCache | None = None,
    enable_rate_limit: bool = True,
    timeout: float = 10.0,
    client: VirusTotalClient | None = None,
) -> VTReputation:
    """Tra cứu thông tin danh tiếng của mã băm SHA-256 qua VirusTotal v3 API.

    Returns:
        VTReputation có thể đọc trực tiếp hoặc giải nén dạng tuple.
    """
    if client is not None:
        return client.lookup_file(sha256)

    c = VirusTotalClient(
        api_key=api_key,
        cache=cache,
        enable_rate_limit=enable_rate_limit,
        timeout=timeout,
    )
    return c.lookup_file(sha256)


# ---------------------------------------------------------------------------
# Hàm kết hợp Heuristic & VirusTotal
# ---------------------------------------------------------------------------


def verify_url_with_vt(
    heuristic_result: UrlFinding,
    *,
    api_key: str | None = None,
    cache: VirusTotalCache | None = None,
    enable_rate_limit: bool = True,
    force_vt: bool = False,
    timeout: float = 10.0,
    client: VirusTotalClient | None = None,
) -> UrlFinding:
    """Xác thực URL với VirusTotal khi kết quả Heuristic ở mức nghi ngờ (SUSPICIOUS).

    Chỉ gọi VirusTotal API khi heuristic_result.status == SafetyStatus.SUSPICIOUS
    (bỏ qua nếu đã SAFE hoặc MALICIOUS, trừ khi force_vt=True).
    """
    if heuristic_result.status != SafetyStatus.SUSPICIOUS and not force_vt:
        return heuristic_result

    rep = lookup_url_reputation(
        heuristic_result.url,
        api_key=api_key,
        cache=cache,
        enable_rate_limit=enable_rate_limit,
        timeout=timeout,
        client=client,
    )
    heuristic_result.reputation = rep

    if rep.error == "no_key":
        heuristic_result.reasons.append(
            Reason(
                code="VT_NO_KEY",
                message="Chưa cấu hình VirusTotal API key, giữ nguyên kết quả heuristic.",
            )
        )
    elif rep.error == "not_found":
        heuristic_result.reasons.append(
            Reason(
                code="VT_NOT_FOUND",
                message="URL chưa có dữ liệu trên VirusTotal, giữ kết quả heuristic.",
            )
        )
    elif rep.error is not None:
        heuristic_result.reasons.append(
            Reason(
                code=f"VT_{rep.error.upper()}",
                message=f"Không thể tra cứu VirusTotal ({rep.error}), fallback về heuristic.",
            )
        )
    elif rep.status is not None:
        if rep.status == SafetyStatus.MALICIOUS:
            heuristic_result.status = SafetyStatus.MALICIOUS
            heuristic_result.reasons.append(
                Reason(
                    code="VT_MALICIOUS",
                    message=f"VirusTotal phát hiện mã độc ({rep.malicious} engine cảnh báo).",
                )
            )
        elif rep.status == SafetyStatus.SUSPICIOUS:
            heuristic_result.status = SafetyStatus.SUSPICIOUS
            heuristic_result.reasons.append(
                Reason(
                    code="VT_SUSPICIOUS",
                    message=(
                        f"VirusTotal đánh giá nghi ngờ ({rep.malicious} malicious, "
                        f"{rep.suspicious} suspicious)."
                    ),
                )
            )
        elif rep.status == SafetyStatus.SAFE:
            heuristic_result.status = SafetyStatus.SAFE
            heuristic_result.reasons.append(
                Reason(
                    code="VT_CLEAN",
                    message=(
                        f"VirusTotal xác nhận an toàn ({rep.harmless} engine không phát hiện)."
                    ),
                )
            )

    return heuristic_result


def verify_attachment_with_vt(
    scan_result: AttachmentScanResult | AttachmentFinding,
    *,
    api_key: str | None = None,
    cache: VirusTotalCache | None = None,
    enable_rate_limit: bool = True,
    force_vt: bool = False,
    allow_suspicious: bool = False,
    email_id: str = "",
    timeout: float = 10.0,
    client: VirusTotalClient | None = None,
) -> AttachmentScanResult | AttachmentFinding:
    """Xác thực file đính kèm với VirusTotal khi kết quả quét Heuristic ở mức nghi ngờ (SUSPICIOUS).

    Chỉ gọi VirusTotal API khi scan_result.status == SafetyStatus.SUSPICIOUS
    (bỏ qua nếu đã SAFE hoặc MALICIOUS, trừ khi force_vt=True).
    Tuân thủ nguyên tắc "Chặn tại cổng": nếu VirusTotal kết luận MALICIOUS, lập tức
    hủy bỏ SafeAttachment (đặt None).
    """
    if scan_result.status != SafetyStatus.SUSPICIOUS and not force_vt:
        return scan_result

    rep = lookup_file_hash(
        scan_result.sha256,
        api_key=api_key,
        cache=cache,
        enable_rate_limit=enable_rate_limit,
        timeout=timeout,
        client=client,
    )

    if isinstance(scan_result, AttachmentScanResult):
        scan_result.reputation = rep

        if rep.error == "no_key":
            scan_result.reasons.append(
                "Chưa cấu hình VirusTotal API key, giữ nguyên kết quả heuristic."
            )
        elif rep.error == "not_found":
            scan_result.reasons.append(
                "Mã băm chưa có dữ liệu trên VirusTotal, giữ kết quả heuristic."
            )
        elif rep.error is not None:
            scan_result.reasons.append(
                f"Không thể tra cứu VirusTotal ({rep.error}), fallback về heuristic."
            )
        elif rep.status is not None:
            if rep.status == SafetyStatus.MALICIOUS:
                scan_result.status = SafetyStatus.MALICIOUS
                scan_result.safe_attachment = None  # Chặn tại cổng!
                scan_result.reasons.append(
                    f"VirusTotal phát hiện mã độc ({rep.malicious} engine cảnh báo)."
                )
            elif rep.status == SafetyStatus.SUSPICIOUS:
                scan_result.status = SafetyStatus.SUSPICIOUS
                if not allow_suspicious:
                    scan_result.safe_attachment = None
                scan_result.reasons.append(
                    f"VirusTotal đánh giá nghi ngờ ({rep.malicious} malicious, "
                    f"{rep.suspicious} suspicious)."
                )
            elif rep.status == SafetyStatus.SAFE:
                scan_result.status = SafetyStatus.SAFE
                scan_result.reasons.append(
                    f"VirusTotal xác nhận an toàn ({rep.harmless} engine không phát hiện)."
                )
                # Nếu chưa có SafeAttachment và có email_id, tạo mới
                if scan_result.safe_attachment is None and email_id:
                    try:
                        scan_result.safe_attachment = SafeAttachment(
                            path=scan_result.file_path,
                            sha256=scan_result.sha256,
                            email_id=email_id,
                        )
                    except Exception:
                        pass

    elif isinstance(scan_result, AttachmentFinding):
        scan_result.reputation = rep

        if rep.error == "no_key":
            scan_result.reasons.append(
                Reason(
                    code="VT_NO_KEY",
                    message="Chưa cấu hình VirusTotal API key, giữ nguyên kết quả heuristic.",
                )
            )
        elif rep.error == "not_found":
            scan_result.reasons.append(
                Reason(
                    code="VT_NOT_FOUND",
                    message="Mã băm chưa có dữ liệu trên VirusTotal, giữ kết quả heuristic.",
                )
            )
        elif rep.error is not None:
            scan_result.reasons.append(
                Reason(
                    code=f"VT_{rep.error.upper()}",
                    message=f"Không thể tra cứu VirusTotal ({rep.error}), fallback về heuristic.",
                )
            )
        elif rep.status is not None:
            if rep.status == SafetyStatus.MALICIOUS:
                scan_result.status = SafetyStatus.MALICIOUS
                scan_result.reasons.append(
                    Reason(
                        code="VT_MALICIOUS",
                        message=f"VirusTotal phát hiện mã độc ({rep.malicious} engine cảnh báo).",
                    )
                )
            elif rep.status == SafetyStatus.SUSPICIOUS:
                scan_result.status = SafetyStatus.SUSPICIOUS
                scan_result.reasons.append(
                    Reason(
                        code="VT_SUSPICIOUS",
                        message=(
                            f"VirusTotal đánh giá nghi ngờ ({rep.malicious} malicious, "
                            f"{rep.suspicious} suspicious)."
                        ),
                    )
                )
            elif rep.status == SafetyStatus.SAFE:
                scan_result.status = SafetyStatus.SAFE
                scan_result.reasons.append(
                    Reason(
                        code="VT_CLEAN",
                        message=(
                            f"VirusTotal xác nhận an toàn ({rep.harmless} engine không phát hiện)."
                        ),
                    )
                )

    return scan_result
