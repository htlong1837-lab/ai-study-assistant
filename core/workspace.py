"""Không gian dữ liệu riêng cho từng người dùng.

Mỗi tài khoản Google đăng nhập có một thư mục riêng ``data/users/<mã>/``, chứa toàn bộ dữ liệu của
người đó: CSDL nhiệm vụ (``app.db``), tiến độ đã học (``progress.json`` cạnh CSDL), thời khoá biểu,
tệp đính kèm đã quét và nhắc nhở. ``<mã>`` là băm SHA-256 của email (không lộ email trên đĩa).

Khách chưa đăng nhập dùng thư mục tạm theo phiên trình duyệt ở ``.cache/guests/<phiên>/``, có dữ
liệu mẫu để dùng thử, không ghi vào dữ liệu của ai và được dọn sau một ngày.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from core import config

USERS_DIR = config.DATA_DIR / "users"
GUESTS_DIR = config.CACHE_DIR / "guests"
GUEST_TTL_SECONDS = 24 * 3600


@dataclass(frozen=True)
class Workspace:
    root: Path
    email: str | None = None  # None: khách

    @property
    def is_guest(self) -> bool:
        return self.email is None

    @property
    def db_path(self) -> Path:
        return self.root / "app.db"

    @property
    def attachments_dir(self) -> Path:
        return self.root / "attachments"

    @property
    def timetable_path(self) -> Path:
        return self.root / "thoi_khoa_bieu.csv"

    @property
    def reminders_path(self) -> Path:
        return self.root / "reminders.json"

    def ensure(self) -> Workspace:
        self.root.mkdir(parents=True, exist_ok=True)
        return self

    def timetable_source(self) -> Path:
        """Thời khoá biểu người dùng đã lưu, nếu chưa có thì bản mẫu."""
        return self.timetable_path if self.timetable_path.is_file() else config.SAMPLE_DIR / "thoi_khoa_bieu.csv"

    def has_own_timetable(self) -> bool:
        return self.timetable_path.is_file()

    def save_timetable(self, data: bytes) -> None:
        self.ensure()
        self.timetable_path.write_bytes(data)

    def reset_timetable(self) -> None:
        self.timetable_path.unlink(missing_ok=True)


def user_key(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:20]


def for_user(email: str, base: Path | None = None) -> Workspace:
    if not email or "@" not in email:
        raise ValueError("Cần email hợp lệ để mở dữ liệu riêng.")
    return Workspace((base or USERS_DIR) / user_key(email), email.strip().lower()).ensure()


def for_guest(session_id: str, base: Path | None = None) -> Workspace:
    safe = re.sub(r"[^A-Za-z0-9_-]", "", session_id)[:64] or "khach"
    return Workspace((base or GUESTS_DIR) / safe).ensure()


def cleanup_guests(base: Path | None = None, ttl: float = GUEST_TTL_SECONDS, now: float | None = None) -> int:
    """Xoá thư mục khách không dùng quá ``ttl`` giây. Trả số thư mục đã xoá."""
    base = base or GUESTS_DIR
    now = now or time.time()
    removed = 0
    for d in base.glob("*") if base.is_dir() else []:
        try:
            if d.is_dir() and now - d.stat().st_mtime > ttl:
                shutil.rmtree(d, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    return removed
