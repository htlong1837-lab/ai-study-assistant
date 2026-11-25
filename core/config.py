"""Cấu hình chung, đọc từ file .env ở thư mục gốc repo."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
SAMPLE_DIR = DATA_DIR / "sample"
CACHE_DIR = ROOT / ".cache"


def env(name: str, default: str = "") -> str:
    """Đọc biến môi trường, bỏ khoảng trắng thừa."""
    return os.getenv(name, default).strip()


DB_PATH = ROOT / env("DB_PATH", "data/app.db")

# Múi giờ của app. Máy chủ đám mây (Streamlit Community Cloud) chạy giờ UTC, nên mọi datetime.now()
# sẽ lệch 7 tiếng so với Việt Nam nếu không đặt lại. Đổi bằng biến môi trường APP_TZ nếu cần.
APP_TZ = env("APP_TZ", "Asia/Ho_Chi_Minh")


def use_app_timezone() -> None:
    """Đặt múi giờ cho cả tiến trình (Linux/macOS). Windows không có time.tzset: dùng giờ của máy."""
    import time

    if not hasattr(time, "tzset"):
        return
    zone = APP_TZ if Path("/usr/share/zoneinfo", APP_TZ).is_file() else ""
    # Không có dữ liệu múi giờ trên máy chủ: dùng chuỗi POSIX (dấu ngược: "ICT-7" nghĩa là UTC+7).
    os.environ["TZ"] = zone or ("ICT-7" if APP_TZ == "Asia/Ho_Chi_Minh" else APP_TZ)
    time.tzset()


use_app_timezone()
