"""Unit tests verifying fallback labeling and cache-pollution prevention."""
from __future__ import annotations

from core.llm_client import LLMClient
from modules.qa.models import Answer


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


def test_shared_client_marks_cache_hits(tmp_path) -> None:
    client = LLMClient(provider="fake", model="fake", cache_dir=tmp_path / "cache")
    first = client.generate("A short test prompt")
    second = client.generate("A short test prompt")
    assert first.cached is False
    assert second.cached is True
