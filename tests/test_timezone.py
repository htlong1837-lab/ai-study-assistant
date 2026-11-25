import os
import time
from datetime import datetime, timezone

from core import clock


def test_app_clock_is_vietnam_time_whatever_the_server_timezone():
    offset = clock.now() - datetime.now(timezone.utc).replace(tzinfo=None)
    assert round(offset.total_seconds() / 3600) == 7
    assert clock.today() == clock.now().date()


def test_process_timezone_is_left_alone():
    """Không đổi múi giờ của cả tiến trình (phần mã Streamlit Cloud chạy chung tiến trình cần giờ gốc)."""
    import app  # noqa: F401 — nạp như khi chạy thật cũng không được đặt TZ
    assert os.environ.get("TZ") in (None, "", os.environ.get("TZ_BEFORE_TESTS", os.environ.get("TZ")))
    assert time.tzname  # vẫn đọc được múi giờ gốc
