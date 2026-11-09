"""Cấu hình Module D — đọc từ .env qua core.config.env().

Không import streamlit hay scikit-learn tại đây để giữ module testable.
Mọi giá trị đều có mặc định hợp lý → ứng dụng chạy được khi thiếu .env.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

# Dùng env() từ core nếu chạy trong repo; fallback os.getenv khi test đơn lẻ.
try:
    from core.config import env as _env
except ImportError:  # pragma: no cover
    def _env(name: str, default: str = "") -> str:  # type: ignore[misc]
        return os.getenv(name, default).strip()


def _parse_whitelist(raw: str) -> list[str]:
    """'uni.edu.vn, hust.edu.vn' → ['uni.edu.vn', 'hust.edu.vn']"""
    return [d.strip().lower() for d in raw.split(",") if d.strip()]


def _parse_int(raw: str, default: int) -> int:
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


@dataclass
class Settings:
    """Toàn bộ tham số cấu hình Module D.

    Khởi tạo không tham số → đọc từ biến môi trường.
    Truyền tường minh → dùng trong test mà không phụ thuộc .env.
    """

    # --- VirusTotal ---
    virustotal_api_key: str = field(default_factory=lambda: _env("VIRUSTOTAL_API_KEY"))
    vt_malicious_threshold: int = field(
        default_factory=lambda: _parse_int(_env("VT_MALICIOUS_THRESHOLD", "3"), 3)
    )
    vt_suspicious_threshold: int = field(
        default_factory=lambda: _parse_int(_env("VT_SUSPICIOUS_THRESHOLD", "5"), 5)
    )

    # --- Domain whitelist ---
    domain_whitelist: list[str] = field(
        default_factory=lambda: _parse_whitelist(
            _env("EMAIL_DOMAIN_WHITELIST", "")
        )
    )

    # --- File đính kèm ---
    attach_max_mb: int = field(
        default_factory=lambda: _parse_int(_env("EMAIL_ATTACH_MAX_MB", "50"), 50)
    )

    # --- LLM ---
    llm_provider: str = field(
        default_factory=lambda: _env("LLM_PROVIDER", "gemini").lower()
    )

    # --- URL shortener blacklist (mở rộng được qua env, cách nhau bằng dấu phẩy) ---
    url_shorteners: list[str] = field(
        default_factory=lambda: _parse_whitelist(
            _env(
                "URL_SHORTENERS",
                "bit.ly,tinyurl.com,t.co,goo.gl,ow.ly,buff.ly,short.io,"
                "rb.gy,cutt.ly,is.gd,v.gd,tiny.cc",
            )
        )
    )

    # --- TLD rủi ro cao ---
    risky_tlds: list[str] = field(
        default_factory=lambda: _parse_whitelist(
            _env("RISKY_TLDS", ".top,.xyz,.click,.tk,.ml,.ga,.cf,.gq,.pw,.cc")
        )
    )

    # --- Regex MSSV/ID để redact trước khi gửi LLM ---
    pii_id_regex: str = field(
        default_factory=lambda: _env("EMAIL_PII_ID_REGEX", r"\b\d{8,10}\b")
    )

    # --- Thư mục lưu file đính kèm (data/real/ — đã gitignore) ---
    attachments_dir: str = field(
        default_factory=lambda: _env("EMAIL_ATTACHMENTS_DIR", "data/real")
    )

    @property
    def has_virustotal(self) -> bool:
        return bool(self.virustotal_api_key)

    @property
    def is_offline_mode(self) -> bool:
        return self.llm_provider == "fake" and not self.has_virustotal

    @property
    def attach_max_bytes(self) -> int:
        return self.attach_max_mb * 1024 * 1024


# Singleton lazy — dùng Settings() trực tiếp trong code production;
# test truyền Settings(...) tường minh với giá trị giả.
def get_settings() -> Settings:
    """Trả Settings từ biến môi trường hiện tại."""
    return Settings()
