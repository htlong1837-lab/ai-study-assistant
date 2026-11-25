"""Tự nạp code mới khi máy chủ kéo bản cập nhật, thay cho bộ theo dõi tệp của Streamlit.

Bộ theo dõi tệp của Streamlit xoá module khỏi ``sys.modules`` ngay khi thấy tệp đổi, kể cả lúc phiên
khác đang nạp đúng module đó; trên Streamlit Cloud (mỗi lần kéo code từ GitHub) việc này làm app hỏng
(``KeyError: 'core'``), nên đã tắt trong ``.streamlit/config.toml``. Thay vào đó, đầu mỗi lần chạy
trang, ``check()`` so dấu vân tay các tệp ``.py`` của app; nếu khác thì — trong một khoá, chỉ một luồng
làm — xoá các module của app khỏi bộ nhớ và xoá bộ đệm mã trang của Streamlit, để lần chạy kế tiếp
dùng code mới. Không cần bấm Reboot sau khi cập nhật.

Module này nằm ngoài các gói của app nên không bao giờ tự bị xoá.
"""
from __future__ import annotations

import hashlib
import importlib
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGES = ("core", "db", "modules", "views")

_LOCK = threading.Lock()


def fingerprint(root: Path = ROOT, packages: tuple[str, ...] = PACKAGES) -> str:
    """Dấu vân tay các tệp .py của app (đường dẫn, thời điểm sửa, kích thước)."""
    h = hashlib.sha256()
    files = [root / "app.py"] + [p for pkg in packages for p in sorted((root / pkg).rglob("*.py"))]
    for p in files:
        try:
            st = p.stat()
        except OSError:
            continue
        h.update(f"{p.relative_to(root)}|{st.st_mtime_ns}|{st.st_size}\n".encode())
    return h.hexdigest()


_current = fingerprint()


def _clear_streamlit_script_cache() -> None:
    try:
        from streamlit.runtime import Runtime

        if Runtime.exists():
            Runtime.instance()._script_cache.clear()  # noqa: SLF001 — không có API công khai
    except Exception:  # noqa: BLE001 — chạy ngoài Streamlit (test): bỏ qua
        pass


def purge(packages: tuple[str, ...] = PACKAGES) -> int:
    """Xoá các module của app khỏi bộ nhớ. Trả số module đã xoá."""
    names = [n for n in list(sys.modules) if n.split(".", 1)[0] in packages]
    for n in names:
        sys.modules.pop(n, None)
    importlib.invalidate_caches()
    return len(names)


def check(root: Path = ROOT, packages: tuple[str, ...] = PACKAGES) -> bool:
    """Có code mới thì nạp lại (một lần, có khoá). Trả ``True`` nếu vừa nạp lại."""
    global _current
    fp = fingerprint(root, packages)
    if fp == _current:
        return False
    with _LOCK:
        if fp == _current:  # luồng khác vừa nạp lại xong
            return False
        purge(packages)
        _clear_streamlit_script_cache()
        _current = fp
    return True
