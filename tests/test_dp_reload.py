import importlib
import os
import sys
import threading

import dp_reload


def test_new_code_is_picked_up_once(tmp_path, monkeypatch):
    pkg = tmp_path / "dpdemo"
    pkg.mkdir()
    (tmp_path / "app.py").write_text("", encoding="utf-8")
    mod = pkg / "greet.py"
    mod.write_text("WORD = 'cũ'\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    packages = ("dpdemo",)
    monkeypatch.setattr(dp_reload, "_current", dp_reload.fingerprint(tmp_path, packages))

    assert importlib.import_module("dpdemo.greet").WORD == "cũ"
    assert dp_reload.check(tmp_path, packages) is False  # chưa đổi gì

    mod.write_text("WORD = 'mới hơn'\n", encoding="utf-8")
    st = mod.stat()
    os.utime(mod, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    assert dp_reload.check(tmp_path, packages) is True
    assert "dpdemo.greet" not in sys.modules
    assert dp_reload.check(tmp_path, packages) is False  # chỉ nạp lại một lần
    assert importlib.import_module("dpdemo.greet").WORD == "mới hơn"
    sys.modules.pop("dpdemo.greet", None)
    sys.modules.pop("dpdemo", None)


def test_many_sessions_at_once_reload_only_once(tmp_path, monkeypatch):
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "p").mkdir()
    packages = ("p",)
    monkeypatch.setattr(dp_reload, "_current", "dấu cũ")
    results = []
    threads = [threading.Thread(target=lambda: results.append(dp_reload.check(tmp_path, packages)))
               for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 1


def test_real_app_fingerprint_covers_app_code():
    fp = dp_reload.fingerprint()
    assert len(fp) == 64 and dp_reload.fingerprint() == fp
