"""WP-06 — Quét an toàn URL offline bằng luật Heuristic (plan_module_d.md § WP-06 & § 6.2).

Không gọi mạng, phân tích dựa trên cấu trúc URL và tên miền:
1. Trỏ trực tiếp đến IP (IPv4 / IPv6) -> SUSPICIOUS (URL_IP_DIRECT).
2. Dịch vụ rút gọn link -> SUSPICIOUS (URL_SHORTENER).
3. Giả mạo tên miền trường học hoặc từ khóa lừa đảo nhạy cảm với domain lạ -> MALICIOUS (URL_SPOOFING).
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from core.contracts import SafetyStatus
from .models import Reason, UrlFinding
from .urls import defang_url

# Các tên miền trường đại học chính thức được công nhận (an toàn)
GENUINE_UNIVERSITY_DOMAINS: list[str] = [
    "hust.edu.vn",
    "vnu.edu.vn",
    "uet.vnu.edu.vn",
    "ptit.edu.vn",
    "fpt.edu.vn",
    "neu.edu.vn",
    "uni.edu.vn",  # domain mẫu của hệ thống
]

# Danh sách dịch vụ rút gọn link phổ biến
SHORTENER_DOMAINS: set[str] = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "gg.gg",
    "cutt.ly",
    "shorturl.at",
    "goo.gl",
    "ow.ly",
    "short.io",
    "rb.gy",
    "is.gd",
    "v.gd",
    "tiny.cc",
}

# Các TLD rủi ro cao thường dùng trong chiến dịch phishing
RISKY_TLDS: set[str] = {
    ".xyz",
    ".top",
    ".tk",
    ".ml",
    ".ga",
    ".cf",
    ".gq",
    ".pw",
    ".cc",
    ".click",
    ".buzz",
    ".cam",
    ".rest",
    ".online",
    ".site",
}

# Các từ khoá / token trường đại học dễ bị giả mạo
UNIVERSITY_TOKENS: set[str] = {
    "hust",
    "vnu",
    "uet",
    "ptit",
    "fpt",
    "neu",
    "eduvn",
    "edu-vn",
    "uni-edu",
    "uni-edu-vn",
}

# Từ khóa lừa đảo nhạy cảm liên quan đến tài khoản / sinh viên
SENSITIVE_PHISHING_KEYWORDS: list[str] = [
    "login",
    "verify",
    "xac-nhan",
    "xacnhan",
    "mat-khau",
    "matkhau",
    "password",
    "tai-khoan",
    "taikhoan",
    "account",
    "banking",
    "hoc-bong",
    "hocbong",
    "trung-thuong",
    "trungthuong",
    "sinhvien",
    "sinh-vien",
    "portal",
    "daotao",
    "dao-tao",
    "bqtac",
    "upgrade",
]


def _is_genuine_university(hostname: str) -> bool:
    """Kiểm tra hostname có thuộc danh sách tên miền trường học hợp lệ hay không."""
    for domain in GENUINE_UNIVERSITY_DOMAINS:
        if hostname == domain or hostname.endswith("." + domain):
            return True
    return False


def _extract_hostname(url: str) -> tuple[str, str | None]:
    """Trích xuất hostname và username/userinfo từ URL. Trả về (hostname, userinfo)."""
    raw = url.strip()
    try:
        p = urlparse(raw)
        if not p.scheme and not raw.startswith("//"):
            p = urlparse("//" + raw)

        host = (p.hostname or "").strip().lower()
        userinfo = p.username
        return host, userinfo
    except Exception:
        return "", None


def scan_url(url: str) -> UrlFinding:
    """Quét và đánh giá mức độ an toàn của một URL theo luật Heuristic offline.

    Args:
        url: Chuỗi URL cần quét.

    Returns:
        UrlFinding với kết quả status (SAFE, SUSPICIOUS, MALICIOUS) và danh sách lý do.
    """
    clean_url = (url or "").strip()
    defanged = defang_url(clean_url)

    if not clean_url:
        return UrlFinding(
            url=clean_url,
            defanged=defanged,
            status=SafetyStatus.SAFE,
            reasons=[],
        )

    hostname, userinfo = _extract_hostname(clean_url)
    if not hostname:
        return UrlFinding(
            url=clean_url,
            defanged=defanged,
            status=SafetyStatus.SAFE,
            reasons=[],
        )

    reasons: list[Reason] = []
    status = SafetyStatus.SAFE

    # 1. Kiểm tra nếu là tên miền trường học chính thức -> SAFE ngay
    if _is_genuine_university(hostname):
        return UrlFinding(
            url=clean_url,
            defanged=defanged,
            status=SafetyStatus.SAFE,
            reasons=[],
        )

    # 2. Kiểm tra link giả mạo bằng thủ đoạn userinfo (@): vd https://hust.edu.vn@evil.com
    if userinfo:
        userinfo_lower = userinfo.lower()
        is_userinfo_spoof = (
            any(d in userinfo_lower for d in GENUINE_UNIVERSITY_DOMAINS)
            or any(t in userinfo_lower for t in UNIVERSITY_TOKENS)
            or "edu" in userinfo_lower
        )
        if is_userinfo_spoof:
            reasons.append(
                Reason(
                    code="URL_SPOOFING",
                    message=(
                        "URL sử dụng ký tự @ để lừa đảo hiển thị tên miền trường học "
                        f"(đích đến thực sự là {hostname})."
                    ),
                )
            )
            return UrlFinding(
                url=clean_url,
                defanged=defanged,
                status=SafetyStatus.MALICIOUS,
                reasons=reasons,
            )

    # 3. Kiểm tra trỏ trực tiếp đến địa chỉ IP (IPv4 / IPv6) -> SUSPICIOUS (URL_IP_DIRECT)
    try:
        ipaddress.ip_address(hostname)
        reasons.append(
            Reason(
                code="URL_IP_DIRECT",
                message="URL trỏ trực tiếp đến địa chỉ IP thay vì tên miền hợp lệ.",
            )
        )
        status = SafetyStatus.SUSPICIOUS
    except ValueError:
        pass

    # 4. Kiểm tra dịch vụ rút gọn link -> SUSPICIOUS (URL_SHORTENER)
    is_shortener = hostname in SHORTENER_DOMAINS or any(
        hostname.endswith("." + s) for s in SHORTENER_DOMAINS
    )
    if is_shortener:
        reasons.append(
            Reason(
                code="URL_SHORTENER",
                message="Dịch vụ rút gọn link che giấu địa chỉ đích thực sự.",
            )
        )
        status = SafetyStatus.SUSPICIOUS

    # 5. Kiểm tra giả mạo / typosquatting trường học hoặc từ khóa lừa đảo -> MALICIOUS (URL_SPOOFING)
    tokens = set(re.split(r"[^a-z0-9]+", hostname))
    h_no_hyphen = hostname.replace("-", "")

    # A: Chứa tên viết tắt trường học hoặc cấu trúc nhái domain trường (hust, vnu, edu-vn...)
    has_school_token = bool(tokens & UNIVERSITY_TOKENS) or any(
        kw in hostname
        for kw in [
            "uni-edu",
            "edu-vn",
            "hust-edu",
            "vnu-edu",
            "neu-edu",
            "ptit-edu",
            "fpt-edu",
        ]
    )
    if has_school_token:
        reasons.append(
            Reason(
                code="URL_SPOOFING",
                message=(
                    f"Tên miền '{hostname}' có dấu hiệu giả mạo trường đại học "
                    "nhưng không thuộc hệ thống tên miền chính thức."
                ),
            )
        )
        return UrlFinding(
            url=clean_url,
            defanged=defanged,
            status=SafetyStatus.MALICIOUS,
            reasons=reasons,
        )

    # B: Chứa từ khóa lừa đảo nhạy cảm đi kèm TLD lạ / rủi ro
    has_risky_tld = any(hostname.endswith(tld) for tld in RISKY_TLDS)
    has_phishing_keyword = any(
        kw in hostname or kw.replace("-", "") in h_no_hyphen
        for kw in SENSITIVE_PHISHING_KEYWORDS
    )

    if has_risky_tld and has_phishing_keyword:
        reasons.append(
            Reason(
                code="URL_SPOOFING",
                message=(
                    f"Tên miền '{hostname}' chứa từ khóa nhạy cảm và sử dụng đuôi tên miền rủi ro cao."
                ),
            )
        )
        return UrlFinding(
            url=clean_url,
            defanged=defanged,
            status=SafetyStatus.MALICIOUS,
            reasons=reasons,
        )

    # C: Chứa domain trường thật dạng lookalike (vd: hust.edu.vn.evil.com)
    for domain in GENUINE_UNIVERSITY_DOMAINS:
        if (
            domain in hostname
            and not hostname.endswith("." + domain)
            and hostname != domain
        ):
            reasons.append(
                Reason(
                    code="URL_SPOOFING",
                    message=(
                        f"Tên miền '{hostname}' lồng ghép tên miền trường '{domain}' "
                        "để đánh lừa người dùng."
                    ),
                )
            )
            return UrlFinding(
                url=clean_url,
                defanged=defanged,
                status=SafetyStatus.MALICIOUS,
                reasons=reasons,
            )

    return UrlFinding(
        url=clean_url,
        defanged=defanged,
        status=status,
        reasons=reasons,
    )


def scan_urls(urls: list[str]) -> list[UrlFinding]:
    """Quét toàn bộ danh sách URL trong email.

    Args:
        urls: Danh sách các URL cần quét.

    Returns:
        Danh sách UrlFinding tương ứng cho từng URL.
    """
    return [scan_url(u) for u in urls]
