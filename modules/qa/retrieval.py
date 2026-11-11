from __future__ import annotations

import math
import re


def rank_pages(question: str, pages, limit: int = 5):
    terms = re.findall(r"\w+", question.lower(), flags=re.UNICODE)
    if not terms:
        return list(pages[:limit])
    docs = [re.findall(r"\w+", page.text.lower(), flags=re.UNICODE) for page in pages]
    avg = sum(map(len, docs)) / max(1, len(docs))
    scored = []
    for index, words in enumerate(docs):
        score = 0.0
        for term in set(terms):
            freq = words.count(term)
            if freq:
                idf = math.log(
                    1
                    + (len(docs) - sum(term in d for d in docs) + 0.5)
                    / (sum(term in d for d in docs) + 0.5)
                )
                score += (
                    idf
                    * freq
                    * 2.2
                    / (freq + 1.2 * (0.25 + 0.75 * len(words) / max(1, avg)))
                )
        scored.append((score, index))
    selected = {i for score, i in sorted(scored, reverse=True)[:limit] if score > 0}
    if not selected:
        selected = set(range(min(limit, len(pages))))
    expanded = selected | {
        i + delta
        for i in tuple(selected)
        for delta in (-1, 1)
        if 0 <= i + delta < len(pages)
    }
    return [p for i, p in enumerate(pages) if i in expanded]
