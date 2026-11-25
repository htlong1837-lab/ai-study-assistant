import pytest

from core import gemini


class M:
    def __init__(self, name, actions=("generateContent",)):
        self.name, self.supported_actions = f"models/{name}", list(actions)


class FakeClient:
    def __init__(self, models):
        self._models = models

    class _Models:
        def __init__(self, outer):
            self.outer = outer

        def list(self):
            return [M(n) for n in self.outer._models] + [M("gemini-9-flash-tts"), M("text-embedding-9")]

    @property
    def models(self):
        return FakeClient._Models(self)


def missing(model):
    return RuntimeError(f"404 NOT_FOUND. {{'error': {{'message': 'models/{model} is not found for API version v1beta'}}}}")


def test_retired_model_falls_back_to_an_available_flash_model(monkeypatch):
    monkeypatch.setattr(gemini, "FALLBACK_MODELS", ())
    gemini._resolved.clear()
    calls = []

    def call(m):
        calls.append(m)
        if m != "gemini-3.1-flash":
            raise missing(m)
        return "ok"

    client = FakeClient(["gemini-3.1-flash", "gemini-3.0-flash"])
    assert gemini.call_with_fallback(client, "gemini-2.5-flash", call, key_id="k") == "ok"
    assert calls[0] == "gemini-2.5-flash" and calls[-1] == "gemini-3.1-flash"
    assert "gemini-9-flash-tts" not in calls
    calls.clear()
    assert gemini.call_with_fallback(client, "gemini-2.5-flash", call, key_id="k") == "ok"
    assert calls == ["gemini-3.1-flash"]  # lần sau dùng luôn model đã tìm được


def test_other_errors_are_not_swallowed(monkeypatch):
    _no_sleep(monkeypatch)
    def call(m):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")
    with pytest.raises(RuntimeError, match="429"):
        gemini.call_with_fallback(FakeClient([]), "x", call)


@pytest.mark.parametrize("raw,expect", [
    ("400 INVALID_ARGUMENT. {'error': {'message': 'API key not valid. Please pass a valid API key.'}}", "không hợp lệ"),
    ("429 RESOURCE_EXHAUSTED. quota", "hết lượt"),
    ("503 UNAVAILABLE. {'error': {'message': 'The model is overloaded.'}}", "quá tải"),
    ("404 NOT_FOUND. {'error': {'message': 'models/gemini-2.5-flash is not found'}}", "Không tìm thấy model"),
    ("400 INVALID_ARGUMENT. {'error': {'message': 'Unsupported MIME type: image/heic'}}", "Unsupported MIME type"),
    ("Something odd AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ012345", "Gemini báo lỗi"),
])
def test_friendly_errors(raw, expect):
    text = gemini.friendly_error(RuntimeError(raw))
    assert expect in text and "AIzaSy" not in text


def _no_sleep(monkeypatch):
    waits = []
    monkeypatch.setattr(gemini, "_sleep", waits.append)
    gemini._resolved.clear()
    return waits


def test_overloaded_model_is_retried_then_succeeds(monkeypatch):
    waits = _no_sleep(monkeypatch)
    answers = iter([RuntimeError("503 UNAVAILABLE. The model is overloaded."), "ok"])

    def call(m):
        a = next(answers)
        if isinstance(a, Exception):
            raise a
        return a
    assert gemini.call_with_fallback(FakeClient([]), "gemini-2.5-flash", call) == "ok"
    assert waits == [1.5]


def test_overloaded_or_out_of_quota_moves_to_another_model(monkeypatch):
    _no_sleep(monkeypatch)
    calls = []

    def call(m):
        calls.append(m)
        if m == "gemini-2.5-flash":
            raise RuntimeError("503 UNAVAILABLE. The model is overloaded.")
        if m == "gemini-3.5-flash":
            raise RuntimeError("429 RESOURCE_EXHAUSTED. quota")
        return f"ok from {m}"
    out = gemini.call_with_fallback(FakeClient([]), "gemini-2.5-flash", call, key_id="k")
    assert out == "ok from gemini-flash-latest"
    assert calls == ["gemini-2.5-flash"] * 3 + ["gemini-3.5-flash", "gemini-flash-latest"]
    assert gemini._resolved == {}  # quá tải là tạm thời: lần sau vẫn thử model chính trước


def test_bad_key_is_reported_immediately(monkeypatch):
    _no_sleep(monkeypatch)
    calls = []

    def call(m):
        calls.append(m)
        raise RuntimeError("400 INVALID_ARGUMENT. API key not valid.")
    with pytest.raises(RuntimeError, match="API key not valid"):
        gemini.call_with_fallback(FakeClient([]), "gemini-2.5-flash", call)
    assert calls == ["gemini-2.5-flash"]


RETIRED = ("404 NOT_FOUND. {'error': {'message': 'This model models/gemini-2.5-flash-lite is no longer available "
           "to new users. Please update your code to use models/gemini-3.5-flash-lite for the latest features.'}}")


def test_suggested_model_is_parsed():
    assert gemini.suggested_model(RuntimeError(RETIRED)) == "gemini-3.5-flash-lite"
    assert gemini.suggested_model(RuntimeError("503 overloaded")) is None


def test_model_google_suggests_is_tried_next(monkeypatch):
    _no_sleep(monkeypatch)
    calls = []

    def call(m):
        calls.append(m)
        if m == "gemini-3.5-flash-lite":
            return "ok"
        raise RuntimeError(RETIRED)
    assert gemini.call_with_fallback(FakeClient([]), "gemini-2.5-flash-lite", call, key_id="k2") == "ok"
    assert calls == ["gemini-2.5-flash-lite", "gemini-3.5-flash-lite"]


def test_real_models_of_the_key_come_before_the_static_list(monkeypatch):
    _no_sleep(monkeypatch)
    client = FakeClient(["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.0-flash", "gemini-flash-latest"])
    assert gemini.available_flash_models(client)[:2] == ["gemini-flash-latest", "gemini-3.5-flash"]
    assert gemini.available_flash_models(client)[-1] == "gemini-3.5-flash-lite"
