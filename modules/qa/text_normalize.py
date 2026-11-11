from __future__ import annotations

import re
import unicodedata


def normalize(text: str) -> str:
    """Normalize extracted PDF text without stripping Vietnamese diacritics."""
    value = unicodedata.normalize("NFC", text or "")
    value = value.translate(
        str.maketrans({"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"})
    )
    value = re.sub(r"-\s*\n\s*", "", value)
    value = value.translate(
        str.maketrans(
            {"“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "–": "-", "—": "-"}
        )
    )
    return re.sub(r"\s+", " ", value).strip().lower()


def match_type(needle: str, haystack: str, threshold: float = 0.9) -> str:
    n, h = normalize(needle), normalize(haystack)
    if not n or not h:
        return "none"
    if n in h:
        return "exact"
    # Longest common contiguous substring; deliberately bounded by the short evidence.
    previous = [0] * (len(h) + 1)
    longest = 0
    for char in n:
        current = [0] * (len(h) + 1)
        for j, other in enumerate(h, 1):
            if char == other:
                current[j] = previous[j - 1] + 1
                longest = max(longest, current[j])
        previous = current
    return "fuzzy" if longest / max(1, len(n)) >= threshold else "none"
