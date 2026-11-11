import unicodedata

import pytest

from core.contracts import Page, ParsedDocument
from modules.qa.reader.selection import locate_selection


@pytest.mark.parametrize(
    ("pages", "page", "selected", "expected_page", "expected_match"),
    [
        (["A sentence on this page."], 1, "A sentence", 1, "exact"),
        (["café is here"], 1, unicodedata.normalize("NFD", "café"), 1, "exact"),
        ([unicodedata.normalize("NFD", "Tiếng Việt")], 1, "Tiếng Việt", 1, "exact"),
        (["inter-\nnational cooperation"], 1, "international cooperation", 1, "exact"),
        (["The ﬁle was saved"], 1, "The file was saved", 1, "exact"),
        (["He said “hello”—then left"], 1, 'He said "hello"-then left', 1, "exact"),
        (["A phrase split\nacross lines."], 1, "phrase split across lines", 1, "exact"),
        (["first page", "target phrase here"], 1, "target phrase", 2, "exact"),
        (["target phrase here", "next page"], 2, "target phrase", 1, "exact"),
        (
            ["The first part of a sentence", "continues on this page."],
            1,
            "part of a sentence continues",
            1,
            "exact",
        ),
        (
            ["inter-", "national cooperation"],
            1,
            "international cooperation",
            1,
            "exact",
        ),
        (["AI supports learning."], 1, "AI", 1, "exact"),
        (["unrelated material"], 1, "missing phrase", 1, "none"),
    ],
)
def test_selection_matching_cases(pages, page, selected, expected_page, expected_match):
    document = ParsedDocument(
        "selection-cases",
        "sample.pdf",
        [Page(number, text) for number, text in enumerate(pages, 1)],
    )
    result = locate_selection(document, page, selected)
    assert result.page == expected_page
    assert result.match_type == expected_match
