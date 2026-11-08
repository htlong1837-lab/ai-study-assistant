"""Unit tests verifying fallback labeling and cache-pollution prevention."""
from __future__ import annotations

from pathlib import Path
from llm_client import LLMClient
from models.answer import Answer


def test_answer_dataclass_supports_source_and_model_used() -> None:
    ans = Answer(
        answer_id="ans-1",
        doc_id="doc-1",
        question_id="q-1",
        text="Sample answer",
        source="local_fallback",
        model_used=None,
    )
    d = ans.to_dict()
    assert d["source"] == "local_fallback"
    assert d["model_used"] is None

    # Backward compatibility: legacy dict without source
    legacy_dict = {
        "answer_id": "ans-2",
        "doc_id": "doc-2",
        "question_id": "q-2",
        "text": "Legacy text",
        "citations": [],
        "status": "draft",
    }
    reconstructed = Answer.from_dict(legacy_dict)
    assert reconstructed.source == "llm"  # defaults to llm


def test_fallback_answer_is_not_written_to_cache(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    client = LLMClient(api_key="test-key", cache_dir=str(cache_dir))

    # Force network failure by using an invalid dummy key and calling generate_answer
    # It will trigger _fallback_answer and return source="local_fallback"
    pages = [{"page_num": 1, "text": "Hanoi is the capital of Vietnam."}]
    res = client.generate_answer("What is the capital?", pages)

    assert res["source"] == "local_fallback"
    assert res["model_used"] is None
    # Crucial security & data integrity assertion: fallback MUST NOT be written to cache!
    key = client.cache_key("What is the capital?", pages, reference_material=True)
    cache_file = cache_dir / f"{key}.json"
    assert not cache_file.exists(), "Fallback response was erroneously written to cache!"
