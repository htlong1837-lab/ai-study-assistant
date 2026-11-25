from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import workspace

ROOT = Path(__file__).resolve().parents[1]
KEY = "AIza" + "x" * 35  # khóa giả đúng định dạng


def _qa(monkeypatch, ws):
    import views._account as account
    import views._gemini as gemini
    monkeypatch.setattr(account, "current", lambda: ws)
    monkeypatch.setattr(gemini, "configured_key", lambda: "")  # máy chạy test có thể có khóa thật
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    return AppTest.from_file(str(ROOT / "views" / "qa.py"), default_timeout=60).run()


def test_save_then_reopen_then_forget(tmp_path, monkeypatch):
    ws = workspace.for_user("sv@gmail.com", base=tmp_path)
    at = _qa(monkeypatch, ws)
    assert not at.exception, at.exception
    assert any("Lấy miễn phí" in e.label for e in at.expander)  # chưa có khóa: có hướng dẫn

    at.text_input(key="qa_api_key_input").input(KEY).run()
    at.button(key="qa_save_key").click().run()
    assert not at.exception, at.exception
    assert ws.read_state("gemini") == {"key": KEY}

    at = _qa(monkeypatch, ws)  # phiên mới
    assert at.session_state["qa_api_key"] == KEY
    assert any("Đã lưu khóa Gemini" in c.value for c in at.caption)
    at.button(key="qa_forget_key").click().run()
    assert ws.read_state("gemini") is None


def test_wrong_looking_key_is_not_saved(tmp_path, monkeypatch):
    ws = workspace.for_user("sv@gmail.com", base=tmp_path)
    at = _qa(monkeypatch, ws)
    at.text_input(key="qa_api_key_input").input("sai-khoa").run()
    at.button(key="qa_save_key").click().run()
    assert ws.read_state("gemini") is None
    assert any("không giống khóa Gemini" in e.value for e in at.error)


def test_guest_is_told_to_sign_in_to_save(tmp_path, monkeypatch):
    ws = workspace.for_guest("phien-khach", base=tmp_path)
    at = _qa(monkeypatch, ws)
    at.text_input(key="qa_api_key_input").input(KEY).run()
    assert not any(b.key == "qa_save_key" for b in at.button)
    assert any("Đăng nhập Google" in c.value for c in at.caption)
