from __future__ import annotations

from dataclasses import dataclass

from core.contracts import ParsedDocument

from ..text_normalize import match_type, normalize


@dataclass
class SelectionMatch:
    page: int
    match_type: str
    start: int = -1
    end: int = -1


def locate_selection(
    document: ParsedDocument, page: int, selected_text: str
) -> SelectionMatch:
    requested = normalize(selected_text)
    pages = sorted(document.pages, key=lambda p: abs(p.number - page))
    for candidate in pages:
        normalized = normalize(candidate.text)
        if requested and requested in normalized:
            return SelectionMatch(
                candidate.number,
                "exact",
                normalized.index(requested),
                normalized.index(requested) + len(requested),
            )
    by_number = {candidate.number: candidate for candidate in document.pages}
    for candidate in pages:
        following = by_number.get(candidate.number + 1)
        if following is None:
            continue
        joined = normalize(candidate.text + "\n" + following.text)
        if requested and requested in joined:
            return SelectionMatch(
                candidate.number,
                "exact",
                joined.index(requested),
                joined.index(requested) + len(requested),
            )
    for candidate in pages:
        kind = match_type(selected_text, candidate.text)
        if kind != "none":
            return SelectionMatch(candidate.number, kind)
    return SelectionMatch(page, "none")
