"""Giờ của app: luôn là giờ Việt Nam, kể cả khi máy chủ chạy giờ UTC (Streamlit Cloud).

Không đặt múi giờ cho cả tiến trình (``TZ`` + ``time.tzset``): như thế cả phần mã của Streamlit Cloud chạy
chung tiến trình cũng đổi giờ, làm trình quản lý của Cloud hiểu sai thời điểm app hoạt động. Code của app
gọi ``now()`` / ``today()`` ở đây thay cho ``datetime.now()`` / ``date.today()``. Kết quả là datetime "naive"
theo giờ Việt Nam, giống cách code cũ dùng ``datetime.now()`` trên máy đặt giờ Việt Nam.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from core import config

try:
    from zoneinfo import ZoneInfo

    APP_TZ = ZoneInfo(config.env("APP_TZ", "Asia/Ho_Chi_Minh"))
except Exception:  # noqa: BLE001 — máy không có dữ liệu múi giờ: Việt Nam không đổi giờ theo mùa
    APP_TZ = timezone(timedelta(hours=7), "ICT")


def now() -> datetime:
    """Giờ hiện tại theo giờ của app, dạng naive (không kèm múi giờ)."""
    return datetime.now(APP_TZ).replace(tzinfo=None)


def today() -> date:
    return now().date()
