import base64

import pytest

from modules.email_security import gmail


class Resp:
    def __init__(self, status, data=None):
        self.status_code, self._data = status, data or {}

    def json(self):
        return self._data


class FakeHttp:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append((url, headers, params))
        return self.routes(url, params)


def _raw(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def test_fetch_lists_inbox_then_reads_raw():
    def routes(url, params):
        if url.endswith("/messages"):
            return Resp(200, {"messages": [{"id": "a"}, {"id": "b"}]})
        return Resp(200, {"raw": _raw(b"Subject: " + url[-1:].encode() + b"\r\n\r\nhi")})
    http = FakeHttp(routes)
    raws = gmail.fetch_recent("tok", days=7, limit=5, http=http)
    assert raws == [b"Subject: a\r\n\r\nhi", b"Subject: b\r\n\r\nhi"]
    url, headers, params = http.calls[0]
    assert headers == {"Authorization": "Bearer tok"}
    assert params == {"q": "in:inbox newer_than:7d", "maxResults": 5}
    assert all(c[2] == {"format": "raw"} for c in http.calls[1:])


@pytest.mark.parametrize("status,exc,msg", [(401, gmail.TokenExpired, "hết hạn"),
                                            (403, gmail.GmailError, "cho phép"),
                                            (500, gmail.GmailError, "500")])
def test_errors_are_friendly(status, exc, msg):
    with pytest.raises(exc, match=msg):
        gmail.fetch_recent("tok", http=FakeHttp(lambda u, p: Resp(status)))


def test_no_token():
    with pytest.raises(gmail.TokenExpired):
        gmail.fetch_recent("", http=FakeHttp(lambda u, p: Resp(200)))


def test_empty_inbox():
    assert gmail.fetch_recent("tok", http=FakeHttp(lambda u, p: Resp(200, {}))) == []
