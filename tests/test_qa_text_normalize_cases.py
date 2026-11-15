import unicodedata

import pytest

from modules.qa.text_normalize import match_type, normalize


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  A   B  ", "a b"),
        ("TIẾNG VIỆT", "tiếng việt"),
        (unicodedata.normalize("NFD", "Tiếng Việt"), "tiếng việt"),
        ("inter-\nnational", "international"),
        ("ﬁle", "file"),
        ("ﬂow", "flow"),
        ("oﬃce", "office"),
        ("ﬀ", "ff"),
        ("ﬄ", "ffl"),
        ("“quoted”", '"quoted"'),
        ("‘quoted’", "'quoted'"),
        ("a—b", "a-b"),
        ("a–b", "a-b"),
        ("line\nbreak", "line break"),
        ("e\u0301", "é"),
    ],
)
def test_normalize_cases(raw, expected):
    assert normalize(raw) == expected


def test_match_type_threshold_and_empty_input():
    assert match_type("abcdefghij", "abcdefghiX", threshold=0.9) == "fuzzy"
    assert match_type("abcdefghij", "abcdeXXXXX", threshold=0.9) == "none"
    assert match_type("", "anything") == "none"
