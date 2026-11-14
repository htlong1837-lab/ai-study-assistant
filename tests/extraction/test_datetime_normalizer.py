from datetime import date, datetime
from pathlib import Path
import pytest
import yaml

from modules.extraction.datetime_normalizer import (
    NormalizedDeadline,
    SemesterConfig,
    normalize,
)

CASES_FILE = Path(__file__).parents[2] / "eval" / "datetime_cases.yaml"


def load_cases():
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("cases", [])


@pytest.mark.parametrize("case", load_cases())
def test_datetime_normalizer_cases(case):
    text = case["text"]
    anchor = datetime.fromisoformat(case["anchor"])
    sem_start = case.get("semester_start")
    semester = SemesterConfig(start_date=date.fromisoformat(sem_start)) if sem_start else None

    result: NormalizedDeadline = normalize(text, anchor, semester)

    expected = case.get("expected")
    if expected is None:
        assert result.value is None, f"Expected None for text '{text}', got {result.value}"
    else:
        assert result.value is not None, f"Expected {expected} for text '{text}', got None"
        exp_dt = datetime.fromisoformat(expected)
        assert result.value == exp_dt, f"Failed for '{text}': got {result.value}, expected {exp_dt}"

    expected_flags = case.get("flags", [])
    for flag in expected_flags:
        assert flag in result.flags, f"Flag {flag} missing in result for '{text}'. Got flags: {result.flags}"

    if "time_defaulted" in case:
        assert result.time_defaulted == case["time_defaulted"], f"time_defaulted mismatch for '{text}'"


def test_determinism_and_no_clock_dependency():
    text = "23h59 thứ 6 tuần sau"
    anchor1 = datetime(2026, 11, 4, 10, 0)
    anchor2 = datetime(2026, 11, 11, 10, 0)

    res1_a = normalize(text, anchor1)
    res1_b = normalize(text, anchor1)
    assert res1_a.value == res1_b.value  # Tính tất định tuyệt đối

    res2 = normalize(text, anchor2)
    # Khác anchor phải cho ra kết quả khác nhau
    assert res1_a.value != res2.value


def test_robustness_against_garbage_input():
    anchor = datetime(2026, 11, 4, 10, 0)
    for bad_input in ["", "   ", "???", "asdfghjk", "1234567890" * 100, None]:
        res = normalize(bad_input, anchor)
        assert res.value is None
        assert "UNRESOLVED" in res.flags
