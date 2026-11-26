"""Hộp thư → danh sách tệp đính kèm để người dùng duyệt từng tệp dùng vào việc gì.

Mỗi tệp: gợi ý mục đích (bài tập, lịch thi, thời khoá biểu, tài liệu học, bỏ qua), người dùng chọn lại
nếu cần rồi duyệt. Lịch thi và thời khoá biểu được đọc thành bảng để người dùng sửa trước khi lưu.
"""
from __future__ import annotations

import io
from collections.abc import Callable
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from core import clock
from core.contracts import SafetyStatus
from db.repository import Repository
from modules.email_security import purpose
from modules.qa.file_readers import IMAGE_MIME, MEDIA_MIME
from modules.scheduler import exams as exam_mod
from modules.scheduler.timetable import load_timetable_csv
from modules.scheduler.timetable_image import (
    FIELDS as TT_FIELDS, MIME as TT_MIME, TimetableImageError, gemini_generate, read_timetable_data,
    to_csv as tt_to_csv,
)
from views import _gemini, _ui

DONE_NOTE = {
    "assignment": "Đã gửi sang Trích xuất bài tập.",
    "exam": "Đã thêm lịch thi vào lịch, kèm giờ ôn thi.",
    "timetable": "Đã lưu làm thời khoá biểu của bạn.",
    "material": "Đã gửi sang Hỏi đáp tài liệu.",
    "skip": "Đã bỏ qua tệp này.",
}
EXAM_COLS = {"mon": "Môn", "ngay": "Ngày (dd/mm/yyyy)", "bat_dau": "Bắt đầu", "ket_thuc": "Kết thúc",
             "phong": "Phòng", "hinh_thuc": "Hình thức", "gio_on": "Giờ ôn"}
TT_COLS = {"thu": "Thứ", "bat_dau": "Bắt đầu", "ket_thuc": "Kết thúc", "mon": "Môn", "phong": "Phòng"}


def _files(items) -> list[tuple]:
    """(tệp, email đã xử lý) của mọi thư không độc, mỗi tệp một lần."""
    seen, out = set(), []
    for p in items:
        if p.email.safety is SafetyStatus.MALICIOUS:
            continue
        for a in p.safe_attachments:
            if a.sha256 not in seen:
                seen.add(a.sha256)
                out.append((a, p))
    return out


def _text(a) -> str:
    """Chữ trong tệp (để gợi ý và đọc lịch thi bằng luật). Ảnh/video không đọc ở đây (cần AI)."""
    cache = st.session_state.setdefault("_att_text", {})
    if a.sha256 in cache:
        return cache[a.sha256]
    doc = (st.session_state.get("verified_documents") or {}).get(a.sha256)
    text = ""
    if doc is not None:
        text = "\n".join(pg.text for pg in doc.pages)
    else:
        path = Path(a.path)
        if path.suffix.lower() not in IMAGE_MIME and path.suffix.lower() not in MEDIA_MIME:
            try:
                from modules.qa.loader import load_document_bytes

                text = "\n".join(pg.text for pg in load_document_bytes(path.name, path.read_bytes()).pages)
            except Exception:  # noqa: BLE001 — tệp hỏng: vẫn cho người dùng chọn mục đích
                text = ""
    cache[a.sha256] = text
    return text


def _forwardable(p) -> bool:
    return p.email.safety is SafetyStatus.SAFE or bool(p.user_approved)


def review(ws, items, forward: Callable[[object], None]) -> None:
    """Vẽ danh sách tệp đính kèm. ``forward(p)`` chuyển email chứa tệp (nếu chưa chuyển)."""
    files = _files(items)
    if not files:
        return
    purpose.sync(ws, st.session_state)
    saved = purpose.decisions(ws)
    pending = [f for f in files if not saved.get(f[0].sha256, {}).get("done")]
    files = pending + [f for f in files if f not in pending]
    st.subheader("📎 Tệp đính kèm")
    st.caption(f"{len(pending)} tệp chờ bạn duyệt · chọn tệp dùng để làm gì, DP chỉ dùng tệp sau khi bạn duyệt."
               if pending else "Đã duyệt hết tệp đính kèm.")
    for a, p in files:
        _one(ws, a, p, saved.get(a.sha256), forward)


def _one(ws, a, p, saved: dict | None, forward) -> None:
    sha, k = a.sha256, a.sha256[:12]
    name = Path(a.path).name
    with st.container(border=True, key=f"att_{k}"):
        c_file, c_state = st.columns([3, 2], vertical_alignment="center")
        c_file.html(f'<div class="nh-chips"><span class="nh-chip" title="sha256: {sha}">'
                    f'{escape(_ui.file_label(name))}</span></div>')
        c_file.caption(f"Từ thư: {p.email.subject}")
        done = bool(saved and saved.get("done"))
        if done:
            c_state.success(purpose.label(saved["purpose"]), icon="✅")
        if not _forwardable(p):
            st.caption("🟡 Thư này đáng ngờ: chọn thư trong bảng bên dưới và xác nhận tin người gửi trước.")
            return
        current = saved["purpose"] if saved else purpose.suggest(name, _text(a))
        choice = st.segmented_control(
            "Dùng tệp này để" if done else "Dùng tệp này để (DP gợi ý, bạn chọn lại nếu chưa đúng)",
            list(purpose.PURPOSES), format_func=purpose.label, default=current, key=f"purp_{k}")
        choice = choice or current
        if done and choice == saved["purpose"]:
            st.caption(DONE_NOTE[choice])
            return
        if choice == "exam":
            _exam(ws, a, p, forward)
        elif choice == "timetable":
            _timetable(ws, a, p)
        else:
            verb = {"assignment": "Gửi sang Trích xuất bài tập", "material": "Gửi sang Hỏi đáp tài liệu",
                    "skip": "Bỏ qua tệp này"}[choice]
            if st.button(verb, key=f"ok_{k}", type="primary" if choice != "skip" else "secondary"):
                if choice != "skip":
                    forward(p)
                purpose.remember(ws, st.session_state, sha, choice)
                st.session_state.pop("sched", None)
                st.toast(DONE_NOTE[choice], icon="📎")
                st.rerun()


def _gemini_rows(ws, a, k: str, read: Callable) -> None:
    """Nút đọc bằng Gemini (cần khóa). ``read(generate)`` trả các dòng."""
    key = _gemini.key_input(f"att_key_{k}", ws=ws)
    if st.button("Đọc bằng Gemini", key=f"gem_{k}", icon=":material/auto_awesome:", disabled=not key):
        from core.llm_client import get_client

        with st.spinner("Gemini đang đọc tệp…"):
            try:
                st.session_state[f"rows_{k}"] = read(gemini_generate(key, get_client().model))
            except (exam_mod.ExamReadError, TimetableImageError) as exc:
                st.error(str(exc), icon="⚠️")
                return
        st.rerun()


def _data_for_gemini(a) -> tuple[bytes, str]:
    path = Path(a.path)
    mime = TT_MIME.get(path.suffix.lower())
    if mime:
        return path.read_bytes(), mime
    return _text(a).encode("utf-8"), "text/plain"


def _exam(ws, a, p, forward) -> None:
    k = a.sha256[:12]
    rows_key = f"rows_{k}"
    if rows_key not in st.session_state:  # bảng chữ: đọc ngay bằng luật, không cần AI
        st.session_state[rows_key] = exam_mod.parse_exam_text(_text(a), clock.today())
    rows = st.session_state[rows_key]
    if not rows:
        st.info("Chưa tự đọc được buổi thi nào trong tệp này (ảnh chụp hoặc bảng phức tạp). "
                "Dùng Gemini để đọc, hoặc tự điền vào bảng.", icon="🔍")
    with st.expander("Đọc bằng Gemini" if rows else "🔑 Đọc bằng Gemini", expanded=not rows):
        _gemini_rows(ws, a, k, lambda gen: exam_mod.read_exam_file(*_data_for_gemini(a), gen, clock.today()))
    st.caption("Kiểm tra từng buổi thi, sửa trực tiếp trong bảng. **Giờ ôn**: số giờ DP xếp để ôn trước buổi thi "
               "(0 = không xếp).")
    edited = st.data_editor(
        pd.DataFrame(rows or [{}], columns=list(exam_mod.FIELDS)), num_rows="dynamic", hide_index=True,
        width="stretch", key=f"exam_edit_{k}",
        column_config={c: (st.column_config.NumberColumn(n, min_value=0.0, max_value=60.0, step=0.5)
                           if c == "gio_on" else n) for c, n in EXAM_COLS.items()})
    data = [{c: ("" if pd.isna(v) else v) for c, v in r.items()} for r in edited.to_dict("records")]
    data = [r for r in data if any(str(v).strip() for c, v in r.items() if c != "gio_on")]
    found, errors = exam_mod.rows_to_exams(data, source=a.sha256[:16])
    for err in errors:
        st.warning(err)
    if st.button(f"💾 Lưu {len(found)} buổi thi vào lịch", key=f"save_exam_{k}", type="primary",
                 disabled=not found or bool(errors)):
        exam_mod.save_exams(ws, found)
        exam_mod.add_review_tasks(Repository(ws.db_path), found)
        purpose.remember(ws, st.session_state, a.sha256, "exam")
        st.session_state.pop("sched", None)
        st.session_state.pop(rows_key, None)
        st.toast(f"Đã thêm {len(found)} buổi thi vào lịch.", icon="🧪")
        st.rerun()


def _timetable(ws, a, p) -> None:
    k = a.sha256[:12]
    path = Path(a.path)
    if path.suffix.lower() == ".csv":
        data = path.read_bytes()
        sessions, errs = load_timetable_csv(io.BytesIO(data))
        for err in errs:
            st.warning(err)
        if st.button(f"💾 Lưu {len(sessions)} buổi làm thời khoá biểu của tôi", key=f"save_tt_{k}",
                     type="primary", disabled=not sessions or bool(errs)):
            ws.save_timetable(data)
            purpose.remember(ws, st.session_state, a.sha256, "timetable")
            st.session_state.pop("sched", None)
            st.toast("Đã lưu thời khoá biểu.", icon="🗓️")
            st.rerun()
        return
    rows_key = f"rows_{k}"
    rows = st.session_state.get(rows_key)
    if rows is None:
        st.caption("Thời khoá biểu trong ảnh, PDF hay bảng Excel/Word được Gemini đọc thành bảng để bạn sửa.")
        _gemini_rows(ws, a, k, lambda gen: read_timetable_data(*_data_for_gemini(a), gen)[0])
        return
    if not rows:
        st.info("Không tìm thấy buổi học nào trong tệp này.", icon="🔍")
    edited = st.data_editor(pd.DataFrame(rows or [{}], columns=list(TT_FIELDS)), num_rows="dynamic",
                            hide_index=True, width="stretch", key=f"tt_edit_{k}", column_config=TT_COLS)
    data = [{c: ("" if pd.isna(v) else str(v)) for c, v in r.items()} for r in edited.to_dict("records")]
    csv_text = tt_to_csv([r for r in data if any(r.values())])
    sessions, errs = load_timetable_csv(io.StringIO(csv_text))
    for err in errs:
        st.warning(err)
    if st.button(f"💾 Lưu {len(sessions)} buổi làm thời khoá biểu của tôi", key=f"save_tt_{k}", type="primary",
                 disabled=not sessions or bool(errs)):
        ws.save_timetable(csv_text.encode("utf-8"))
        purpose.remember(ws, st.session_state, a.sha256, "timetable")
        st.session_state.pop("sched", None)
        st.session_state.pop(rows_key, None)
        st.toast("Đã lưu thời khoá biểu.", icon="🗓️")
        st.rerun()
