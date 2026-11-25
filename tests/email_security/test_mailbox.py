import imaplib
from datetime import date

import pytest

from modules.email_security.mailbox import MailboxError, fetch_recent, imap_date, imap_host


class FakeImap:
    def __init__(self, messages: dict[bytes, bytes], password: str = "abcdefghijklmnop"):
        self.messages, self.password = messages, password
        self.calls: list[tuple] = []

    def login(self, user, pw):
        self.calls.append(("login", user, pw))
        if pw != self.password:
            raise imaplib.IMAP4.error("AUTHENTICATIONFAILED")
        return "OK", [b""]

    def select(self, box, readonly=False):
        self.calls.append(("select", box, readonly))
        return "OK", [str(len(self.messages)).encode()]

    def search(self, charset, *criteria):
        self.calls.append(("search", *criteria))
        return "OK", [b" ".join(self.messages)]

    def fetch(self, msg_id, what):
        self.calls.append(("fetch", msg_id, what))
        return "OK", [(msg_id + b" (BODY[] {3}", self.messages[msg_id]), b")"]

    def logout(self):
        self.calls.append(("logout",))


def test_imap_host_and_date():
    assert imap_host("SV@Gmail.com") == "imap.gmail.com"
    assert imap_host("sv@uni.edu.vn") is None
    assert imap_date(date(2026, 3, 5)) == "05-Mar-2026"


def test_fetch_is_readonly_newest_first_and_limited():
    box = FakeImap({b"1": b"m1", b"2": b"m2", b"3": b"m3"})
    raws = fetch_recent("sv@gmail.com", "abcd efgh ijkl mnop", days=7, limit=2,
                        today=date(2026, 11, 25), connect=lambda h: box)
    assert raws == [b"m3", b"m2"]
    assert ("select", "INBOX", True) in box.calls
    assert ("search", "SINCE", "18-Nov-2026") in box.calls
    assert all(c[2] == "(BODY.PEEK[])" for c in box.calls if c[0] == "fetch")  # không đánh dấu đã đọc
    assert box.calls[0] == ("login", "sv@gmail.com", "abcdefghijklmnop")  # bỏ dấu cách của Google
    assert box.calls[-1] == ("logout",)


def test_wrong_password_gives_friendly_error_and_logs_out():
    box = FakeImap({}, password="right")
    with pytest.raises(MailboxError, match="mật khẩu ứng dụng"):
        fetch_recent("sv@gmail.com", "wrong", connect=lambda h: box)
    assert box.calls[-1] == ("logout",)


def test_unknown_domain_needs_host():
    with pytest.raises(MailboxError, match="imap.gmail.com"):
        fetch_recent("sv@uni.edu.vn", "x", connect=lambda h: FakeImap({}))
    box = FakeImap({b"1": b"m"}, password="x")
    assert fetch_recent("sv@uni.edu.vn", "x", host="imap.gmail.com", connect=lambda h: box) == [b"m"]


def test_connection_failure():
    def boom(host):
        raise OSError("timed out")
    with pytest.raises(MailboxError, match="Không kết nối được"):
        fetch_recent("sv@gmail.com", "x", connect=boom)


# ---------------------------------------------------------------- trang Hộp thư
def _inbox_app(monkeypatch, fake_fetch):
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    import modules.email_security.mailbox as mailbox
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setattr(mailbox, "fetch_recent", fake_fetch)
    root = Path(__file__).resolve().parents[2]
    return AppTest.from_file(str(root / "views" / "email_security.py"), default_timeout=30).run()


def test_inbox_page_connects_and_scans(monkeypatch):
    demo = sorted((__import__("pathlib").Path(__file__).resolve().parents[2] / "data" / "demo").glob("*.eml"))
    seen = {}

    def fake_fetch(address, password, **kw):
        seen.update(address=address, password=password, **kw)
        return [p.read_bytes() for p in demo]

    at = _inbox_app(monkeypatch, fake_fetch)
    assert not at.exception
    at.text_input[0].input("sv@gmail.com")
    at.text_input[1].input("abcd efgh ijkl mnop")
    next(b for b in at.button if b.label == "Kết nối").click().run()
    assert not at.exception, at.exception
    assert seen["address"] == "sv@gmail.com" and seen["days"] == 14
    assert len(at.session_state["processed_list"]) == len(demo)


def test_inbox_page_shows_login_error(monkeypatch):
    def fake_fetch(*a, **kw):
        raise MailboxError("Đăng nhập không thành công.")

    at = _inbox_app(monkeypatch, fake_fetch)
    at.text_input[0].input("sv@gmail.com")
    at.text_input[1].input("sai")
    next(b for b in at.button if b.label == "Kết nối").click().run()
    assert not at.exception
    assert any("Đăng nhập không thành công" in e.value for e in at.error)


def test_google_button_explains_missing_setup(monkeypatch):
    at = _inbox_app(monkeypatch, lambda *a, **k: [])
    assert not at.exception
    at.button(key="google_login").click().run()
    assert not at.exception, at.exception
    assert any("docs/dang-nhap-google.md" in e.value for e in at.error)
