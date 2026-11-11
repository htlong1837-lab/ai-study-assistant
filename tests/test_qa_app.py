from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def test_main_app_and_qa_view_initialize_without_exceptions():
    for relative in ("app.py", "views/qa.py"):
        app = AppTest.from_file(str(ROOT / relative)).run()
        assert not app.exception, [str(error.message) for error in app.exception]


def test_qa_view_accepts_key_in_session_without_config_file():
    app = AppTest.from_file(str(ROOT / "views" / "qa.py")).run()
    app.text_input[0].set_value("test-key-not-real").run()
    assert app.session_state["qa_api_key"] == "test-key-not-real"
    app.button[0].click().run()
    assert "qa_api_key" not in app.session_state
    assert app.session_state["qa_key_cleared"] is True


def test_app_clears_qa_key_when_leaving_reader_page():
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    app.switch_page("views/qa.py").run()
    app.session_state["qa_api_key"] = "test-key-not-real"
    app.session_state["qa_api_key_input"] = "test-key-not-real"
    app.switch_page("views/home.py").run()
    assert "qa_api_key" not in app.session_state
    assert "qa_api_key_input" not in app.session_state
