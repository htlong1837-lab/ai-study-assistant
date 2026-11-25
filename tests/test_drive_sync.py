import io
import re
import zipfile

import pytest

from db.repository import Repository
from modules.storage import drive_sync as ds


class Resp:
    def __init__(self, status=200, data=None, content=b""):
        self.status_code, self._data, self.content = status, data or {}, content

    def json(self):
        return self._data


class FakeDrive:
    """Drive trong bộ nhớ: đủ list/get/create/update cho drive_sync."""

    def __init__(self):
        self.files: dict[str, dict] = {}
        self.clock = 0
        self.calls: list[str] = []

    def _tick(self):
        self.clock += 1
        return f"2026-11-25T09:00:{self.clock:02d}Z"

    def get(self, url, params=None, headers=None, timeout=None):
        assert headers["Authorization"] == "Bearer tok"
        if url == ds.FILES:
            self.calls.append("list")
            assert "appProperties has" in params["q"]
            files = sorted(self.files.values(), key=lambda f: f["modifiedTime"], reverse=True)
            return Resp(data={"files": [{"id": f["id"], "modifiedTime": f["modifiedTime"]} for f in files]})
        fid = url.rsplit("/", 1)[1]
        self.calls.append("download")
        return Resp(content=self.files[fid]["data"])

    def post(self, url, params=None, data=None, headers=None, timeout=None):
        self.calls.append("create")
        boundary = re.search(r"boundary=(\S+)", headers["Content-Type"]).group(1).encode()
        parts = data.split(b"--" + boundary)
        assert b'"appProperties": {"dp": "workspace-v1"}' in parts[1]
        payload = parts[2].split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n", 1)[0]
        fid = f"f{len(self.files) + 1}"
        self.files[fid] = {"id": fid, "data": payload, "modifiedTime": self._tick()}
        return Resp(data={"id": fid})

    def patch(self, url, params=None, data=None, headers=None, timeout=None):
        self.calls.append("update")
        fid = url.rsplit("/", 1)[1]
        self.files[fid].update(data=data, modifiedTime=self._tick())
        return Resp(data={"id": fid})


def _task(root, tid, title):
    Repository(root / "app.db").create_task({
        "id": tid, "title": title, "course": "CSDL", "deadline": "2026-12-20T23:59:00", "estimated_hours": 2.0,
        "priority": "medium", "confidence": 0.9, "status": "confirmed", "created_at": "2026-11-25T08:00:00+00:00"})


def test_backup_then_restore_on_a_fresh_server(tmp_path):
    drive = FakeDrive()
    laptop = tmp_path / "laptop"
    laptop.mkdir()
    _task(laptop, "t-1", "Đồ án CSDL")
    (laptop / "thoi_khoa_bieu.csv").write_text("thu,bat_dau,ket_thuc,mon,phong\n", encoding="utf-8")
    (laptop / "attachments").mkdir()
    (laptop / "attachments" / "to.pdf").write_bytes(b"%PDF-" + b"x" * 100)

    assert ds.save(laptop, "tok", drive) is True
    assert ds.save(laptop, "tok", drive) is False  # không đổi gì thì không tải lên lại
    names = zipfile.ZipFile(io.BytesIO(drive.files["f1"]["data"])).namelist()
    assert "app.db" in names and "thoi_khoa_bieu.csv" in names
    assert not any(n.startswith("attachments") or n.endswith(("-wal", "-shm")) for n in names)

    server = tmp_path / "server"  # máy chủ mới khởi động lại: ổ đĩa trống
    assert ds.restore(server, "tok", drive) is True
    assert [t["title"] for t in Repository(server / "app.db").list_tasks()] == ["Đồ án CSDL"]
    assert ds.restore(server, "tok", drive) is False  # đã có đúng bản đó

    _task(server, "t-2", "Thuyết trình")
    assert ds.save(server, "tok", drive) is True
    assert drive.calls.count("create") == 1 and drive.calls.count("update") == 1  # ghi đè, không tạo tệp mới
    assert ds.restore(laptop, "tok", drive) is True
    assert len(Repository(laptop / "app.db").list_tasks()) == 2


def test_restore_ignores_paths_escaping_the_folder(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("../evil.txt", "x")
        z.writestr("ok.txt", "y")
    ds.unpack(tmp_path / "ws", buf.getvalue())
    assert (tmp_path / "ws" / "ok.txt").read_text() == "y"
    assert not (tmp_path / "evil.txt").exists()


@pytest.mark.parametrize("status,msg", [(401, "hết hạn"), (403, "Chưa được phép"), (500, "500")])
def test_drive_errors(tmp_path, status, msg):
    class Bad:
        def get(self, *a, **k):
            return Resp(status)
    with pytest.raises(ds.DriveError, match=msg):
        ds.restore(tmp_path, "tok", Bad())


def test_empty_folder_is_not_uploaded(tmp_path):
    assert ds.save(tmp_path / "none", "tok", FakeDrive()) is False
