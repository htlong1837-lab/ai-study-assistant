"""Cửa gọi LLM dùng chung cho mọi module (constitution: bảo mật và dữ liệu).

    from core.llm_client import get_client, LLMNotConfigured
    client = get_client()
    try:
        resp = client.generate("Tóm tắt email sau: ...", system="Trả lời bằng tiếng Việt")
    except LLMNotConfigured as e:
        st.warning(str(e))

Cache theo nội dung yêu cầu trong .cache/llm/, thống kê trong .cache/llm/usage.json.
Thêm nhà cung cấp: viết hàm _call_<tên> rồi đăng ký vào PROVIDERS.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from . import config


class LLMNotConfigured(RuntimeError):
    """Thiếu khóa API, thiếu thư viện hoặc nhà cung cấp không tồn tại."""


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached: bool = False


# --- nhà cung cấp: (model, system, prompt, temperature, api_key) -> (text, in_tok, out_tok) ---


def _call_fake(model, system, prompt, temperature, api_key):
    text = "[fake] " + prompt[:80]
    return text, len(f"{system or ''} {prompt}".split()), len(text.split())


def _call_gemini(model, system, prompt, temperature, api_key, timeout=None):
    from google import genai
    from google.genai import types

    if timeout is None:
        client = genai.Client(api_key=api_key)
    else:
        client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout * 1000))
        )
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system, temperature=temperature
        ),
    )
    meta = resp.usage_metadata
    return (
        resp.text or "",
        getattr(meta, "prompt_token_count", 0) or 0,
        getattr(meta, "candidates_token_count", 0) or 0,
    )


def _gemini_installed() -> bool:
    try:
        import google.genai  # noqa: F401

        return True
    except ImportError:
        return False


PROVIDERS: dict[str, Callable] = {"fake": _call_fake, "gemini": _call_gemini}
NEEDS_KEY = {"gemini"}
_EMPTY_USAGE = {"calls": 0, "cache_hits": 0, "input_tokens": 0, "output_tokens": 0}


class LLMClient:
    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str = "",
        cache_dir: Path | str | None = None,
    ):
        self.provider = provider
        self.model = model
        self._api_key = api_key
        self.cache_dir = Path(cache_dir) if cache_dir else config.CACHE_DIR / "llm"

    # --- trạng thái ---

    def not_configured_reason(self) -> str | None:
        if self.provider not in PROVIDERS:
            return f"Nhà cung cấp LLM '{self.provider}' không được hỗ trợ ({', '.join(PROVIDERS)})."
        if self.provider in NEEDS_KEY and not self._api_key:
            return f"Chưa có khóa API cho '{self.provider}'. Điền vào file .env để bật chức năng AI."
        if self.provider == "gemini" and not _gemini_installed():
            return "Chưa cài thư viện google-genai (pip install -r requirements.txt)."
        return None

    def is_configured(self) -> bool:
        return self.not_configured_reason() is None

    # --- gọi ---

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.0,
        use_cache: bool = True,
        timeout: float | None = None,
    ) -> LLMResponse:
        if timeout is not None and timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        reason = self.not_configured_reason()
        if reason:
            raise LLMNotConfigured(reason)

        path = self.cache_dir / f"{self._key(prompt, system, temperature)}.json"
        if use_cache:
            hit = self._read_cache(path)
            if hit is not None:
                self._add_usage(cache_hits=1)
                return hit

        provider = PROVIDERS[self.provider]
        if self.provider == "gemini" and timeout is not None:
            text, in_tok, out_tok = provider(
                self.model, system, prompt, temperature, self._api_key, timeout=timeout
            )
        else:
            text, in_tok, out_tok = provider(
                self.model, system, prompt, temperature, self._api_key
            )
        resp = LLMResponse(text=text, input_tokens=in_tok, output_tokens=out_tok)
        self._add_usage(calls=1, input_tokens=in_tok, output_tokens=out_tok)
        if use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(asdict(resp), ensure_ascii=False), encoding="utf-8"
            )
        return resp

    def usage(self) -> dict:
        try:
            data = json.loads(
                (self.cache_dir / "usage.json").read_text(encoding="utf-8")
            )
            return {**_EMPTY_USAGE, **data}
        except (OSError, ValueError):
            return dict(_EMPTY_USAGE)

    # --- nội bộ ---

    def _key(self, prompt, system, temperature) -> str:
        raw = json.dumps(
            [self.provider, self.model, system, prompt, temperature], ensure_ascii=False
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _read_cache(path: Path) -> LLMResponse | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return LLMResponse(**{**data, "cached": True})
        except (OSError, ValueError, TypeError):
            return None

    def _add_usage(self, **delta) -> None:
        usage = self.usage()
        for k, v in delta.items():
            usage[k] += v
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "usage.json").write_text(json.dumps(usage), encoding="utf-8")


def get_client() -> LLMClient:
    """Client theo cấu hình trong .env."""
    provider = config.env("LLM_PROVIDER", "gemini").lower()
    return LLMClient(
        provider=provider,
        model=config.env("LLM_MODEL", "gemini-2.5-flash"),
        api_key=config.env(f"{provider.upper()}_API_KEY"),
    )
