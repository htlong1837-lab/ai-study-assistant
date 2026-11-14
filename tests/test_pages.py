from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
VIEWS = sorted(p for p in (ROOT / "views").glob("*.py") if not p.name.startswith("_"))


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch, tmp_path):
    """Chạy như máy lạ: không khóa API, cache riêng."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setattr("core.config.CACHE_DIR", tmp_path)


def test_all_five_pages_exist():
    assert {p.stem for p in VIEWS} == {"home", "qa", "extraction", "scheduler", "email_security"}


@pytest.mark.parametrize("page", VIEWS, ids=lambda p: p.stem)
def test_page_runs_without_api_key(page):
    at = AppTest.from_file(str(page), default_timeout=30).run()
    assert not at.exception, at.exception


def test_app_entry_runs():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not at.exception, at.exception
    assert "Trợ lý AI học tập" in at.title[0].value


def test_home_warns_ai_off():
    at = AppTest.from_file(str(ROOT / "views" / "home.py"), default_timeout=30).run()
    assert any("đang tắt" in w.value for w in at.warning)


def test_scheduler_runs_both_algorithms():
    at = AppTest.from_file(str(ROOT / "views" / "scheduler.py"), default_timeout=60).run()
    assert not at.exception
    at.button(key="run").click().run()
    assert not at.exception, at.exception
    metrics = at.dataframe[1].value  # [0] là bảng xác nhận nhiệm vụ
    assert list(metrics.columns) == ["EDF", "CP-SAT"]
    assert set(metrics.loc["Xung đột"]) == {"0"}
