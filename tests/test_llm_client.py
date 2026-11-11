import pytest

from core.llm_client import LLMClient, LLMNotConfigured


def test_gemini_without_key_is_not_configured(tmp_path):
    client = LLMClient(provider="gemini", model="m", api_key="", cache_dir=tmp_path)
    assert client.is_configured() is False
    with pytest.raises(LLMNotConfigured):
        client.generate("xin chào")


def test_unknown_provider_is_not_configured(tmp_path):
    client = LLMClient(provider="khong-co", model="m", api_key="k", cache_dir=tmp_path)
    assert client.is_configured() is False
    with pytest.raises(LLMNotConfigured):
        client.generate("x")


def test_fake_provider_and_cache(tmp_path):
    client = LLMClient(provider="fake", model="m", cache_dir=tmp_path)
    first = client.generate("hạn nộp là khi nào", system="trả lời ngắn")
    second = client.generate("hạn nộp là khi nào", system="trả lời ngắn")
    assert first.text.startswith("[fake]") and not first.cached
    assert second.cached and second.text == first.text
    usage = client.usage()
    assert usage["calls"] == 1 and usage["cache_hits"] == 1
    assert usage["input_tokens"] == first.input_tokens > 0


def test_cache_key_depends_on_inputs(tmp_path):
    client = LLMClient(provider="fake", model="m", cache_dir=tmp_path)
    client.generate("a")
    assert client.generate("a", system="khác").cached is False
    assert client.generate("a", temperature=0.5).cached is False
    assert client.generate("a", use_cache=False).cached is False


def test_corrupt_cache_file_is_ignored(tmp_path):
    client = LLMClient(provider="fake", model="m", cache_dir=tmp_path)
    client.generate("a")
    for f in tmp_path.glob("*.json"):
        if f.name != "usage.json":
            f.write_text("{hỏng", encoding="utf-8")
    assert client.generate("a").cached is False


def test_usage_persists_between_instances(tmp_path):
    LLMClient(provider="fake", model="m", cache_dir=tmp_path).generate("a")
    assert LLMClient(provider="fake", model="m", cache_dir=tmp_path).usage()["calls"] == 1


def test_optional_timeout_is_forwarded_only_when_requested(monkeypatch, tmp_path):
    from core import llm_client

    calls = []

    def provider(model, system, prompt, temperature, api_key, *, timeout=None):
        calls.append(timeout)
        return "ok", 1, 1

    monkeypatch.setitem(llm_client.PROVIDERS, "gemini", provider)
    client = LLMClient(
        provider="gemini", model="m", api_key="key", cache_dir=tmp_path
    )
    monkeypatch.setattr(client, "not_configured_reason", lambda: None)
    client.generate("without timeout", use_cache=False)
    client.generate("with timeout", use_cache=False, timeout=9)
    assert calls == [None, 9]


def test_timeout_must_be_positive(tmp_path):
    client = LLMClient(provider="fake", model="m", cache_dir=tmp_path)
    with pytest.raises(ValueError, match="greater than zero"):
        client.generate("question", timeout=0)
