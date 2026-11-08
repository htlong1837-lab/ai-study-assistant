"""Security utility functions for Module A."""
from __future__ import annotations

import re

# Patterns that look like API secrets and should be masked in logs/error messages.
_SECRET_PATTERNS = [
    # Google AI / GenAI keys: AQ. prefix
    re.compile(r"\bAQ\.[A-Za-z0-9_\-]{20,}\b"),
    # Google API keys: AIza prefix
    re.compile(r"\bAIza[A-Za-z0-9_\-]{30,}\b"),
    # OpenAI / generic sk- keys
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    # Generic long alphanumeric tokens (40+ hex chars)
    re.compile(r"\b[A-Za-z0-9]{40,}\b"),
]

_MASK = "****"


def mask_secrets(text: str) -> str:
    """Replace recognisable API-key patterns in *text* with ``****``.

    Every log message or error string that might echo back user-supplied
    credentials must pass through this function before being written to any
    output stream.
    """
    if not text:
        return text
    result = text
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub(_MASK, result)
    return result
