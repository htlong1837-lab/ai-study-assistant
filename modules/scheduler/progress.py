"""Lưu khối học nào đã làm xong, để đánh dấu trên dòng thời gian và tính tiến độ.

Lưu thành file JSON nằm cạnh CSDL (cùng thư mục với DB_PATH), nên mỗi CSDL có tiến độ riêng.
Khoá của một khối: "<task_id>@<giờ bắt đầu ISO>".
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def block_key(task_id: str, start: datetime) -> str:
    return f"{task_id}@{start:%Y-%m-%dT%H:%M}"


class ProgressStore:
    def __init__(self, db_path: Path | str):
        self.path = Path(db_path).with_name("progress.json")

    def done(self) -> set[str]:
        try:
            return set(json.loads(self.path.read_text(encoding="utf-8")))
        except (FileNotFoundError, ValueError):
            return set()

    def set_done(self, key: str, value: bool) -> set[str]:
        keys = self.done()
        (keys.add if value else keys.discard)(key)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(sorted(keys), ensure_ascii=False), encoding="utf-8")
        return keys
