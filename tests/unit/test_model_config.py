"""Unit tests for model catalogue configuration and cascade."""
from __future__ import annotations

import config
from llm_client import LLMClient


def test_model_cascade_loaded_from_config() -> None:
    cascade = config.get_model_cascade()
    assert isinstance(cascade, list)
    assert len(cascade) >= 3
    # Check that modern models are present in cascade
    assert "gemini-4-argon" in cascade or "gemini-3.8-flash" in cascade or "gemini-2.5-flash" in cascade


def test_estimate_cost_calculation() -> None:
    # 1,000 input tokens on gemini-4-argon ($2.00 / 1M = $0.002 / 1K)
    cost = config.estimate_cost("gemini-4-argon", input_tokens=1000, output_tokens=0)
    assert cost is not None
    assert round(cost, 4) == 0.002

    # Unknown model should return None
    assert config.estimate_cost("unknown-model", 100, 100) is None


def test_llm_client_candidate_models_respects_config(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODEL_CASCADE", "gemini-test-1,gemini-test-2")
    client = LLMClient(api_key="test-key", model="gemini-primary")
    candidates = client._candidate_models()

    assert candidates[0] == "gemini-primary"
    assert "gemini-test-1" in candidates
    assert "gemini-test-2" in candidates
