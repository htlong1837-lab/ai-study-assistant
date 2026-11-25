"""Sao lưu lịch riêng của mỗi người vào Google Drive của chính họ.

Khi chạy trên máy chủ không giữ ổ đĩa (Streamlit Community Cloud xoá ổ đĩa mỗi lần khởi động lại),
dữ liệu trong ``data/users/<mã>/`` sẽ mất. Module này đóng gói thư mục đó thành một tệp zip nhỏ
(``DP - Daily Planner (du lieu).zip``) trong Drive của người dùng và tải về khi họ đăng nhập lại.

Quyền dùng là ``drive.file``: DP chỉ thấy đúng các tệp do DP tạo, không đọc được tệp khác trong Drive.
Tệp đính kèm email (có thể lớn, và lấy lại được từ Gmail) không được đưa vào bản sao lưu.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import sqlite3
import uuid
import zipfile
from pathlib import Path
from typing import Any

import requests

SCOPE = "https://www.googleapis.com/auth/drive.file"
FILES = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
NAME = "DP - Daily Planner (du lieu).zip"
TAG = {"dp": "workspace-v1"}
SKIP_DIRS = {"attachments", "inbox"}  # lấy lại được từ Gmail; tránh đưa thư thô lên Drive
MAX_BYTES = 10 * 1024 * 1024
MARKER = ".drive.json"  # ghi id tệp và dấu vân tay lần đồng bộ cuối

log = logging.getLogger(__name__)


class DriveError(Exception):
    pass


def _files(root: Path) -> list[Path]:
    out = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if (p.is_file() and rel.parts[0] not in SKIP_DIRS and p.name != MARKER
                and not p.name.endswith(("-journal", "-wal", "-shm"))):
            out.append(p)
    return out


def _checkpoint(root: Path) -> None:
    """Gộp nhật ký WAL vào tệp .db để bản sao lưu có đủ thay đổi mới nhất."""
    for db in root.glob("*.db"):
        try:
            with sqlite3.connect(db) as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        except sqlite3.Error as exc:
            log.warning("Không gộp được WAL của %s: %s", db.name, exc)


def fingerprint(root: Path) -> str:
    """Dấu vân tay nội dung thư mục (không gồm tệp đính kèm) để biết có gì mới cần lưu không."""
    _checkpoint(root)
    h = hashlib.sha256()
    for p in _files(root):
        h.update(str(p.relative_to(root)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def pack(root: Path) -> bytes:
    _checkpoint(root)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in _files(root):
            z.write(p, p.relative_to(root).as_posix())
    data = buf.getvalue()
    if len(data) > MAX_BYTES:
        raise DriveError("Dữ liệu quá lớn để sao lưu.")
    return data


def unpack(root: Path, data: bytes) -> None:
    """Giải nén bản sao lưu vào ``root``; bỏ qua mọi đường dẫn thoát ra ngoài thư mục."""
    root.mkdir(parents=True, exist_ok=True)
    base = root.resolve()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            target = (root / info.filename).resolve()
            if info.is_dir() or base not in target.parents:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(info))


def read_marker(root: Path) -> dict:
    try:
        return json.loads((root / MARKER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_marker(root: Path, **fields) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / MARKER).write_text(json.dumps({**read_marker(root), **fields}), encoding="utf-8")


# --------------------------------------------------------------------------- gọi Drive API
def _check(r) -> Any:
    if r.status_code == 401:
        raise DriveError("Phiên Google đã hết hạn.")
    if r.status_code == 403:
        raise DriveError("Chưa được phép lưu vào Google Drive (cần đăng nhập lại và cho phép).")
    if r.status_code >= 400:
        raise DriveError(f"Google Drive trả lỗi {r.status_code}.")
    return r


def find(token: str, http: Any = None) -> dict | None:
    """Tệp sao lưu DP trong Drive (id, modifiedTime), hoặc ``None``."""
    http = http or requests
    q = (f"name = '{NAME}' and trashed = false and "
         f"appProperties has {{ key='dp' and value='{TAG['dp']}' }}")
    r = _check(http.get(FILES, headers={"Authorization": f"Bearer {token}"}, timeout=20,
                        params={"q": q, "spaces": "drive", "orderBy": "modifiedTime desc",
                                "fields": "files(id,modifiedTime)", "pageSize": 1}))
    files = r.json().get("files", [])
    return files[0] if files else None


def download(token: str, file_id: str, http: Any = None) -> bytes:
    http = http or requests
    r = _check(http.get(f"{FILES}/{file_id}", params={"alt": "media"},
                        headers={"Authorization": f"Bearer {token}"}, timeout=30))
    return r.content


def upload(token: str, data: bytes, file_id: str | None = None, http: Any = None) -> str:
    """Tạo mới hoặc ghi đè tệp sao lưu. Trả id tệp."""
    http = http or requests
    auth = {"Authorization": f"Bearer {token}"}
    if file_id:
        r = _check(http.patch(f"{UPLOAD}/{file_id}", params={"uploadType": "media"}, data=data,
                              headers={**auth, "Content-Type": "application/zip"}, timeout=30))
        return r.json().get("id", file_id)
    boundary = f"dp-{uuid.uuid4().hex}"
    meta = json.dumps({"name": NAME, "mimeType": "application/zip", "appProperties": TAG})
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
            f"--{boundary}\r\nContent-Type: application/zip\r\n\r\n").encode() + data + f"\r\n--{boundary}--".encode()
    r = _check(http.post(UPLOAD, params={"uploadType": "multipart", "fields": "id"}, data=body,
                         headers={**auth, "Content-Type": f"multipart/related; boundary={boundary}"}, timeout=30))
    return r.json()["id"]


# --------------------------------------------------------------------------- hai thao tác chính
def restore(root: Path, token: str, http: Any = None) -> bool:
    """Đầu phiên: nếu Drive có bản sao lưu mới hơn lần đồng bộ cuối trên máy này thì tải về.
    Trả ``True`` nếu đã khôi phục."""
    remote = find(token, http)
    if remote is None:
        return False
    marker = read_marker(root)
    if marker.get("file_id") == remote["id"] and marker.get("modified") == remote.get("modifiedTime"):
        return False  # máy này đã có đúng bản đó
    unpack(root, download(token, remote["id"], http))
    write_marker(root, file_id=remote["id"], modified=remote.get("modifiedTime"), fp=fingerprint(root))
    return True


def save(root: Path, token: str, http: Any = None) -> bool:
    """Sau mỗi lần thay đổi: tải bản mới lên nếu nội dung khác lần đồng bộ cuối. Trả ``True`` nếu đã lưu."""
    if not root.is_dir() or not _files(root):
        return False
    fp = fingerprint(root)
    marker = read_marker(root)
    if marker.get("fp") == fp:
        return False
    file_id = marker.get("file_id")
    if not file_id:
        remote = find(token, http)
        file_id = remote["id"] if remote else None
    file_id = upload(token, pack(root), file_id, http)
    remote = find(token, http)
    write_marker(root, file_id=file_id, modified=(remote or {}).get("modifiedTime"), fp=fp)
    return True
