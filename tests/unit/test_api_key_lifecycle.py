"""Unit tests for API key lifecycle, isolation, and error handling."""
from __future__ import annotations

import pytest
from errors import MissingAPIKeyError
from llm_client import LLMClient
from qa_service import QAService
from utils.security import mask_secrets


def test_llm_client_missing_key_raises_error() -> None:
    with pytest.raises(MissingAPIKeyError):
        LLMClient(api_key="")

    with pytest.raises(MissingAPIKeyError):
        LLMClient(api_key="   ")

    with pytest.raises(MissingAPIKeyError):
        LLMClient(api_key=None)  # type: ignore[arg-type]


def test_qa_service_missing_key_raises_error() -> None:
    with pytest.raises(MissingAPIKeyError):
        QAService(api_key=None, llm_client=None)

    with pytest.raises(MissingAPIKeyError):
        QAService(api_key="", llm_client=None)


def test_llm_client_instances_are_isolated() -> None:
    client_a = LLMClient(api_key="key-for-user-A", model="gemini-2.5-flash")
    client_b = LLMClient(api_key="key-for-user-B", model="gemini-4-argon")

    assert client_a.api_key == "key-for-user-A"
    assert client_b.api_key == "key-for-user-B"
    assert client_a.model != client_b.model


def test_mask_secrets() -> None:
    assert mask_secrets("") == ""
    assert mask_secrets("Hello world") == "Hello world"
    
    # Check Google AI AQ. key
    leaked_aq = "AQ." + ("x" * 40)
    masked = mask_secrets(f"Error connecting with {leaked_aq} to Gemini")
    assert leaked_aq not in masked
    assert "****" in masked

    # Check Google AIza key
    fake_aiza = "AIzaSyD-1234567890abcdefghijklmnopqrstuv"
    masked_aiza = mask_secrets(f"Token is {fake_aiza}")
    assert fake_aiza not in masked_aiza
    assert "****" in masked_aiza
