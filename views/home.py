"""Trang chủ: bảng "Hôm nay" — lời chào, tiến độ tuần, dòng thời gian hôm nay, hạn nộp sắp tới,
thêm nhanh nhiệm vụ, lối vào 4 module."""
from dataclasses import replace
from datetime import datetime, timedelta

import streamlit as st

from core import config
from core.config import SAMPLE_DIR
from core.contracts import TaskStatus
from db.repository import Repository
from modules.scheduler import schedule
from modules.scheduler.model import WEEKDAY_VN, ScheduleSettings
from modules.scheduler.progress import ProgressStore, block_key
from modules.scheduler.slots import busy_intervals
from modules.scheduler.source import tasks_from_b
from modules.scheduler.timetable import load_timetable_csv
from views import _planner, _timeline, _ui
from views._shared import llm_status

_ui.intro()
now = datetime.now()
today = now.date()
repo = Repository(config.DB_PATH)
tasks, _ = tasks_from_b(repo)
done = ProgressStore(config.DB_PATH).done()
colors = _planner.task_colors(tasks)

# Lịch: dùng kết quả đã xếp ở trang Lập lịch nếu có, không thì xếp nhanh bằng EDF cho 7 ngày.
run = st.session_state.get("sched")
if run and isinstance(run.get("settings"), ScheduleSettings):
    result = next(iter(run["results"].values()))
    sessions, settings = run["sessions"], run["settings"]
    plan_note = f"Theo lịch bạn đã xếp ({result.algorithm})."
else:
    sessions, _err = load_timetable_csv(SAMPLE_DIR / "thoi_khoa_bieu.csv")
    settings = ScheduleSettings(start=today, days=7, not_before=now)
    result = schedule(tasks, sessions, settings, "EDF")
    plan_note = "Gợi ý nhanh (EDF, thời khoá biểu mẫu). Mở Lập lịch để tối ưu bằng CP-SAT."

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
    f'<div class="nh-hero"><div><h1>{_ui.greeting(now)} 👋</h1>'
    '<p>Email, đề bài và lịch học của bạn — gom lại thành một nhịp học đều đặn. '
    '<b>AI chỉ đề xuất</b>, bạn là người quyết định.</p>'
    + "".join(f'<span class="nh-chip">{c}</span>' for c in chips)
    + f"</div>{_ui.ring(done_week, len(week_blocks), 'tuần này')}</div>")

st.write("")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Nhiệm vụ đang theo", sum(t.status is TaskStatus.CONFIRMED for t in tasks))
k2.metric("Chờ bạn xác nhận", sum(t.status is TaskStatus.PROPOSED for t in tasks))
k3.metric("Khối học tuần này", len(week_blocks), f"{done_week} đã xong" if done_week else None)
processed = st.session_state.get("processed_list") or []
k4.metric("Email đã chặn", sum(not p.can_forward for p in processed) if processed else "—",
          help="Đếm trong phiên này, sau khi bạn tải email ở trang Email & bảo mật.")

# ---------------------------------------------------------------- Hôm nay + sắp đến hạn
left, right = st.columns([3, 2], gap="large")
with left:
    with st.container(border=True):
        st.markdown(f"#### 🗓️ Hôm nay · {date_vn}")
        st.caption(plan_note)
        items = _planner.day_items(today, result.blocks, tasks, sessions, settings, done, colors)
        st.html(_timeline.render(items, now))
        _ui.link("views/scheduler.py", "Mở lịch đầy đủ", "📅")
    with st.container(border=True):
        st.markdown("#### 📊 Nhịp tuần")
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
        st.caption("Viết như nói chuyện — hệ thống tự đọc hạn nộp, số giờ, độ gấp.")
        _planner.quick_add(repo, sorted({s.course for s in sessions}), key="home")

# ---------------------------------------------------------------- Lối vào các module
st.markdown("#### Luồng xử lý")
blurbs = {"D": "Quét link & tệp, chặn email độc", "B": "Đọc email, đề bài → nhiệm vụ có hạn",
          "C": "Xếp khối tự học quanh thời khoá biểu", "A": "Hỏi tài liệu, trả lời kèm số trang"}
for col, (code, name, icon, color, page) in zip(st.columns(4), _ui.MODULES):
    with col:
        st.html(f'<div class="nh-mod" style="--c:{color}"><div class="i">{icon}</div>'
                f'<b>{name}</b><span>{blurbs[code]}</span></div>')
        _ui.link(page, "Mở trang →")

with st.expander("Trạng thái hệ thống & sơ đồ kỹ thuật"):
    llm_status()
    st.graphviz_chart(
        """
        digraph {
          rankdir=LR; bgcolor="transparent"; node [shape=box, style="rounded,filled",
          fillcolor="#FFF4EC", color="#F3D9D2", fontname="Helvetica"];
          mail [label="Email (.eml)"];
          D [label="D · Email & bảo mật\\nphân loại, quét link/file"];
          block [label="Chặn\\n(độc)", shape=octagon, fillcolor="#FFE3E3"];
          A [label="A · Hỏi đáp tài liệu\\nđọc PDF theo trang"];
          B [label="B · Trích xuất bài tập\\nhạn nộp, yêu cầu"];
          ok [label="Bạn xác nhận", shape=diamond];
          C [label="C · Lập lịch & nhắc nhở\\nEDF / CP-SAT"];
          mail -> D; D -> block [style=dashed]; D -> B; D -> A [label="file an toàn"];
          A -> B [label="văn bản"]; B -> ok; ok -> C;
        }
        """
    )
