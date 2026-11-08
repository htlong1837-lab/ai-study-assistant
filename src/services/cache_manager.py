from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional


class CacheManager:
    def __init__(self, cache_dir: str = ".cache/llm"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        cache_path = self.cache_dir / f"{self._hash(key)}.json"
        if not cache_path.exists():
            return None
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def set(self, key: str, payload: Dict[str, Any]) -> None:
        cache_path = self.cache_dir / f"{self._hash(key)}.json"
        cache_path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True), encoding="utf-8")
