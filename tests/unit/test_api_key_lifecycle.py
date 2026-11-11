"""Unit tests for API key lifecycle, isolation, and error handling."""
from __future__ import annotations

from core.llm_client import LLMClient


def test_shared_client_without_key_reports_unconfigured() -> None:
    client = LLMClient(provider="gemini", model="gemini-2.5-flash")
    assert not client.is_configured()


def test_llm_client_instances_are_isolated() -> None:
    client_a = LLMClient(provider="gemini", api_key="key-for-user-A", model="gemini-2.5-flash")
    client_b = LLMClient(provider="gemini", api_key="key-for-user-B", model="gemini-2.5-flash")

    assert client_a._api_key == "key-for-user-A"
    assert client_b._api_key == "key-for-user-B"
    assert client_a._api_key != client_b._api_key
