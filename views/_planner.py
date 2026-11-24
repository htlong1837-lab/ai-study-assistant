"""Phần dùng chung giữa Trang chủ và trang Lập lịch: dựng dòng thời gian một ngày, danh sách sắp
đến hạn, ô thêm nhanh nhiệm vụ."""
from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import date, datetime
from html import escape

import streamlit as st

from core.contracts import StudyBlock, Task, TaskStatus
from db.repository import Repository
from modules.scheduler.model import ClassSession, ScheduleSettings
from modules.scheduler.progress import block_key
from modules.scheduler.quick_add import parse
from modules.scheduler.slots import busy_intervals
from views import _timeline

PRIORITY_VN = {"high": "Cao", "medium": "Vừa", "low": "Thấp"}


def task_colors(tasks: list[Task]) -> dict[str, str]:
    return {t.id: _timeline.PALETTE[i % len(_timeline.PALETTE)] for i, t in enumerate(tasks)}


def day_items(day: date, blocks: list[StudyBlock], tasks: list[Task], sessions: list[ClassSession],
              settings: ScheduleSettings, done: set[str], colors: dict[str, str]) -> list[_timeline.Item]:
    titles = {t.id: t.title for t in tasks}
    day_sessions = busy_intervals(sessions, replace(settings, start=day, days=1, not_before=None))
    items = [_timeline.Item(b0, b1, s.course, f"Lên lớp · {s.room}" if s.room else "Lên lớp", "🏫",
                            _timeline.CLASS_COLOR) for b0, b1, s in day_sessions]
    items += [_timeline.Item(b.start, b.end, titles.get(b.task_id, b.task_id), "Tự học", "📖",
                             colors.get(b.task_id, _timeline.PALETTE[0]),
                             done=block_key(b.task_id, b.start) in done)
              for b in blocks if b.start.date() == day]
    items += [_timeline.Item(t.deadline, t.deadline, f"Hạn nộp: {t.title}", t.course, "📌",
                             _timeline.DEADLINE_COLOR)
              for t in tasks if t.status is TaskStatus.CONFIRMED and t.deadline.date() == day]
    return items


def _left(delta_s: float) -> tuple[str, str, str]:
    """(nhãn còn lại, màu chữ, màu nền) theo độ gấp."""
    if delta_s < 0:
        return "Quá hạn", "#fff", "#E63946"
    d, rem = divmod(int(delta_s), 86400)
    h = rem // 3600
    label = f"còn {d} ngày {h} giờ" if d else f"còn {h} giờ" if h else "dưới 1 giờ"
    if delta_s < 86400:
        return label, "#fff", "#F07167"
    if delta_s < 3 * 86400:
        return label, "#9A3412", "#FFE8D6"
    return label, "#3F6212", "#E9F5DB"


def upcoming_html(tasks: list[Task], now: datetime, colors: dict[str, str], limit: int = 6) -> str:
    rows = sorted((t for t in tasks if t.status is TaskStatus.CONFIRMED
                   and (t.deadline - now).total_seconds() > -86400), key=lambda t: t.deadline)[:limit]
    if not rows:
        return '<div class="tl-empty">Không có hạn nộp nào sắp tới. 🎈</div>'
    out = []
    for t in rows:
        label, fg, bg = _left((t.deadline - now).total_seconds())
        out.append(
            f'<div class="nh-due"><div class="dot" style="background:{colors.get(t.id, "#F07167")}"></div>'
            f'<div class="t">{escape(t.title)}<div class="c">{escape(t.course)} · '
            f'{t.deadline:%H:%M %d/%m} · ưu tiên {PRIORITY_VN[t.priority.value].lower()}</div>'
            f'<span class="left" style="color:{fg};background:{bg}">{label}</span></div></div>')
    return "".join(out)


def quick_add(repo: Repository, courses: list[str], key: str) -> None:
    """Ô thêm nhiệm vụ bằng một câu tiếng Việt. Người dùng tự nhập nên nhiệm vụ được xác nhận luôn."""
    if st.session_state.pop(f"qa_clear_{key}", False):
        st.session_state[f"qa_text_{key}"] = ""  # xoá ô sau khi thêm (trước khi ô được vẽ)
    with st.form(f"qa_form_{key}", clear_on_submit=False, border=False):
        text = st.text_input(
            "Thêm nhanh", key=f"qa_text_{key}", label_visibility="collapsed",
            placeholder="✨ “Báo cáo CSDL 23h59 thứ Sáu, 3 giờ, gấp”")
        preview = st.form_submit_button("Xem trước")
    if not (text.strip() and (preview or st.session_state.get(f"qa_ready_{key}") == text)):
        return
    st.session_state[f"qa_ready_{key}"] = text
    q = parse(text, datetime.now(), courses)
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
        title = c1.text_input("Nhiệm vụ", q.title, key=f"qa_title_{key}")
        deadline = c2.text_input("Hạn nộp", f"{q.deadline:%H:%M %d/%m/%Y}" if q.deadline else "",
                                 key=f"qa_dl_{key}", help="Dạng HH:MM dd/mm/yyyy")
        hours = c3.number_input("Số giờ", 0.5, 40.0, float(q.hours), step=0.5, key=f"qa_h_{key}")
        prio = c4.selectbox("Ưu tiên", ["high", "medium", "low"],
                            index=["high", "medium", "low"].index(q.priority.value),
                            format_func=PRIORITY_VN.get, key=f"qa_p_{key}")
        st.caption(f"Môn: **{q.course}**" + "".join(f" · {n}" for n in q.notes))
        if st.button("➕ Thêm vào lịch", type="primary", key=f"qa_add_{key}"):
            try:
                dl = datetime.strptime(deadline.strip(), "%H:%M %d/%m/%Y")
            except ValueError:
                st.error("Hạn nộp chưa đúng dạng HH:MM dd/mm/yyyy.")
                return
            if not title.strip():
                st.error("Nhiệm vụ cần có tên.")
                return
            tid = f"q-{uuid.uuid4().hex[:8]}"
            repo.create_task({
                "id": tid, "title": title.strip(), "course": q.course, "deadline": dl.isoformat(),
                "estimated_hours": hours, "priority": prio, "confidence": 1.0, "status": "confirmed",
                "created_at": datetime.now().isoformat()})
            repo.add_sources(tid, [{"source": "manual:quick-add", "field": "title",
                                    "quote": text.strip(), "kind": "manual"}])
            st.session_state.pop(f"qa_ready_{key}", None)
            st.session_state[f"qa_clear_{key}"] = True
            st.session_state.pop("sched", None)  # lịch cũ không còn đúng
            st.toast(f"Đã thêm “{title.strip()}” — hạn {dl:%H:%M %d/%m}", icon="✅")
            st.rerun()
