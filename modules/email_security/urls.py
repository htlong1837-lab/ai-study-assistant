"""Trích xuất và chuẩn hoá URL (WP-01, plan_module_d.md § WP-01 & § 6.2).

Không phụ thuộc thư viện ngoài — chỉ dùng re, urllib.parse từ stdlib.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlparse, urlunparse

# Regex tìm URL trong văn bản thuần (không parse HTML)
_URL_RE = re.compile(
    r"""
    (?:https?|ftp)://          # scheme bắt buộc
    (?:[^\s\[\]<>\"'(){}\|\\]+ # ký tự URL hợp lệ
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Ký tự thừa thường bám cuối URL trong văn bản tự nhiên
_TRAILING_JUNK = re.compile(r"[.,;:!?)>\]'\"]+$")


def extract_urls(text: str, html_links: list[tuple[str, str]] | None = None) -> list[str]:
    """Trích tất cả URL từ văn bản thuần và/hoặc danh sách liên kết HTML.

    Args:
        text: Văn bản thuần (body email).
        html_links: [(link_text, href)] từ thẻ <a> trong HTML. Có thể None.

    Returns:
        Danh sách URL đã chuẩn hoá, không trùng lặp, giữ thứ tự xuất hiện đầu tiên.
    """
    seen: dict[str, None] = {}  # dict giữ thứ tự (Python 3.7+)

    # 1. URL trong plain text
    for m in _URL_RE.finditer(text):
        url = _TRAILING_JUNK.sub("", m.group(0))
        normalized = normalize_url(url)
        if normalized:
            seen.setdefault(normalized, None)

    # 2. href từ thẻ <a>
    if html_links:
        for _link_text, href in html_links:
            normalized = normalize_url(href)
            if normalized:
                seen.setdefault(normalized, None)

    return list(seen)


def normalize_url(url: str) -> str:
    """Chuẩn hoá URL: lowercase scheme+host, bỏ fragment, giữ path/query.

    Trả về chuỗi rỗng nếu URL không parse được hoặc không có hostname.
    """
    url = url.strip()
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in {"http", "https", "ftp"}:
            return ""
        if not parsed.netloc:
            return ""
        # Chuẩn hoá: scheme và host lowercase, bỏ fragment
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            parsed.query,
            "",  # bỏ fragment
        ))
        return normalized
    except Exception:
        return ""


def defang_url(url: str) -> str:
    """Chuyển URL sang dạng defang để hiển thị an toàn (không clickable).

    Áp dụng:
    - ``http://`` → ``hxxp://``
    - ``https://`` → ``hxxps://``
    - ``ftp://`` → ``fxp://``
    - Dấu chấm trong hostname → ``[.]``

    >>> defang_url("http://evil.example.com/path")
    'hxxp://evil[.]example[.]com/path'
    >>> defang_url("https://uni.edu.vn/login")
    'hxxps://uni[.]edu[.]vn/login'
    """
    if not url:
        return url
    try:
        parsed = urlparse(url)
        # Defang scheme
        scheme_map = {"http": "hxxp", "https": "hxxps", "ftp": "fxp"}
        defanged_scheme = scheme_map.get(parsed.scheme.lower(), parsed.scheme)

        # Defang hostname (chỉ dấu chấm trong netloc, không đụng port hay userinfo)
        netloc = parsed.netloc
        # Tách userinfo, host, port để chỉ defang phần host
        if "@" in netloc:
            userinfo, hostpart = netloc.rsplit("@", 1)
        else:
            userinfo, hostpart = None, netloc

        if ":" in hostpart:
            host, port = hostpart.rsplit(":", 1)
        else:
            host, port = hostpart, None

        defanged_host = host.replace(".", "[.]")
        defanged_netloc = defanged_host
        if port:
            defanged_netloc += f":{port}"
        if userinfo:
            defanged_netloc = f"{userinfo}@{defanged_netloc}"

        defanged = urlunparse((
            defanged_scheme,
            defanged_netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        ))
        return defanged
    except Exception:
        # Fallback: thay thủ công
        return (
            url.replace("http://", "hxxp://")
               .replace("https://", "hxxps://")
               .replace(".", "[.]", 1)  # ít nhất 1 chấm
        )


class _LinkExtractor(HTMLParser):
    """HTMLParser nhẹ để lấy (link_text, href) từ thẻ <a>."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            attr_dict = dict(attrs)
            self._current_href = attr_dict.get("href") or ""
            self._current_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href is not None:
            text = "".join(self._current_text).strip()
            self.links.append((text, self._current_href))
            self._current_href = None
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)


def extract_html_links(html: str) -> list[tuple[str, str]]:
    """Trích (link_text, href) từ HTML. Trả danh sách rỗng nếu parse lỗi."""
    try:
        extractor = _LinkExtractor()
        extractor.feed(html)
        return extractor.links
    except Exception:
        return []
