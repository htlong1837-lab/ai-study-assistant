"""Unit tests verifying zero disk side-effects during LLMClient construction."""
from __future__ import annotations

from pathlib import Path
from llm_client import LLMClient


def test_llm_client_instantiation_creates_no_files_or_directories(tmp_path: Path) -> None:
    cache_dir = tmp_path / "lazy_cache"
    assert not cache_dir.exists()

    # Instantiation should NOT create the cache directory (lazy creation)
    client = LLMClient(api_key="dummy-key", cache_dir=str(cache_dir))
    assert not cache_dir.exists(), "Cache directory was eagerly created on construction!"

    # No stray .env or config file should be created in tmp_path
    created_items = list(tmp_path.iterdir())
    assert not created_items, f"Unexpected files or directories created: {created_items}"

    # Directory is only created when writing cache
    client._write_cache("test_key", {"answer": "hello"})
    assert cache_dir.exists(), "Cache directory should exist after writing cache"
    assert (cache_dir / "test_key.json").exists()
