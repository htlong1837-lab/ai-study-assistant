import time
from datetime import datetime, timezone

import pytest

from core import config


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="Windows dùng giờ của máy, không đặt lại múi giờ")
def test_app_runs_on_vietnam_time_even_on_a_utc_server():
    config.use_app_timezone()
    offset = datetime.now() - datetime.now(timezone.utc).replace(tzinfo=None)
    assert round(offset.total_seconds() / 3600) == 7
