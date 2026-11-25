"""Trang chủ: bảng "Hôm nay" — lời chào, tiến độ tuần, dòng thời gian hôm nay, hạn nộp sắp tới,
thêm nhanh nhiệm vụ, lối vào 4 module."""
from dataclasses import replace
from datetime import datetime, timedelta

import streamlit as st

from core.contracts import TaskStatus
from db.repository import Repository
from modules.scheduler import schedule
from modules.scheduler.model import WEEKDAY_VN, ScheduleSettings
from modules.scheduler.progress import ProgressStore, block_key
from modules.scheduler.slots import busy_intervals
from modules.scheduler.source import tasks_from_b
from modules.scheduler.timetable import load_timetable_csv
from views import _account, _planner, _timeline, _ui

now = datetime.now()
today = now.date()
ws = _account.current()
repo = Repository(ws.db_path)
tasks, _ = tasks_from_b(repo)
done = ProgressStore(ws.db_path).done()
colors = _planner.task_colors(tasks)

# Lịch: dùng kết quả đã xếp ở trang Lập lịch nếu có, không thì xếp nhanh bằng EDF cho 7 ngày.
run = st.session_state.get("sched")
if run and isinstance(run.get("settings"), ScheduleSettings):
    result = next(iter(run["results"].values()))
    sessions, settings = run["sessions"], run["settings"]
else:
    sessions, _err = load_timetable_csv(ws.timetable_source())
    settings = ScheduleSettings(start=today, days=7, not_before=now)
    result = schedule(tasks, sessions, settings, "EDF")

week_start = today - timedelta(days=today.weekday())
week_blocks = [b for b in result.blocks if week_start <= b.start.date() < week_start + timedelta(days=7)]
done_week = sum(block_key(b.task_id, b.start) in done for b in week_blocks)
today_blocks = [b for b in result.blocks if b.start.date() == today]
due_week = [t for t in tasks if t.status is TaskStatus.CONFIRMED
            and timedelta(0) <= t.deadline - now <= timedelta(days=7)]

# ---------------------------------------------------------------- Hero
date_vn = f"{WEEKDAY_VN[today.weekday()]}, {today:%d/%m/%Y}"
chips = [f"📅 {date_vn}", f"📌 {len(due_week)} hạn trong 7 ngày",
         f"📖 {sum(b.hours for b in today_blocks):g} giờ tự học hôm nay"]
st.html(
    f'<div class="nh-hero"><div><h1>{_ui.greeting(now)}</h1>'
    '<div class="nh-chips">' + "".join(f'<span class="nh-chip">{c}</span>' for c in chips)
    + f"</div></div>{_ui.ring(done_week, len(week_blocks), 'tuần này')}</div>")

st.write("")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Đang theo", sum(t.status is TaskStatus.CONFIRMED for t in tasks))
k2.metric("Chờ duyệt", sum(t.status is TaskStatus.PROPOSED for t in tasks))
k3.metric("Khối học tuần", len(week_blocks), f"{done_week} đã xong" if done_week else None)
processed = st.session_state.get("processed_list") or []
k4.metric("Email chặn", sum(not p.can_forward for p in processed) if processed else "—",
          help="Đếm trong phiên này, sau khi bạn tải email ở trang Hộp thư.")

# ---------------------------------------------------------------- Hôm nay + sắp đến hạn
left, right = st.columns([3, 2], gap="large")
with left:
    with st.container(border=True):
        st.markdown(f"#### 🗓️ Hôm nay · {date_vn}")
        items = _planner.day_items(today, result.blocks, tasks, sessions, settings, done, colors)
        st.html(_timeline.render(items, now))
        _ui.link("views/scheduler.py", "Mở lịch đầy đủ", "📅")
    with st.container(border=True):
        st.markdown("#### 📊 Tuần này")
        days7 = [week_start + timedelta(days=i) for i in range(7)]
        study_h = {d: sum(b.hours for b in week_blocks if b.start.date() == d) for d in days7}
        class_h = {}
        for b0, b1, _s in busy_intervals(sessions, replace(settings, start=week_start, days=7, not_before=None)):
            class_h[b0.date()] = class_h.get(b0.date(), 0) + (b1 - b0).total_seconds() / 3600
        st.html(_ui.week_bars(days7, study_h, class_h, today))
with right:
    with st.container(border=True):
        st.markdown("#### ⏳ Sắp đến hạn")
        st.html(_planner.upcoming_html(tasks, now, colors))
    with st.container(border=True):
        st.markdown("#### ✨ Thêm nhanh")
        _planner.quick_add(repo, sorted({s.course for s in sessions}), key="home")

