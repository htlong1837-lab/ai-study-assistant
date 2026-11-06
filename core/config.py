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
