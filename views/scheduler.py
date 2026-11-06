from dataclasses import replace
from datetime import date, datetime, time, timedelta

import altair as alt
import pandas as pd
import streamlit as st

from core import mocks
from core.config import SAMPLE_DIR
from core.contracts import TaskStatus
from modules.scheduler import ALGORITHMS, schedule
from modules.scheduler.metrics import evaluate
from modules.scheduler.model import WEEKDAY_VN, ScheduleSettings
from modules.scheduler.reminders import (
    TelegramSender, make_reminders, save_reminders, send_due, to_ics,
)
from modules.scheduler.slots import busy_intervals
from modules.scheduler.timetable import load_timetable_csv
from views._shared import module_header

module_header("📅 Lập lịch & nhắc nhở", "Long (C)",
              "Task đã xác nhận (từ B), thời khoá biểu CSV",
              "Khối học, nhắc nhở Telegram, file .ics")

# ---------------------------------------------------------------- 1. Nhiệm vụ
st.subheader("1. Nhiệm vụ")
st.caption("AI chỉ đề xuất: chỉ nhiệm vụ được tích **Xác nhận** mới được xếp vào lịch. "
           "Hiện dùng dữ liệu mẫu, sẽ thay bằng kết quả của module B.")
base_tasks = mocks.tasks()  # TODO: thay bằng nhiệm vụ do module B lưu khi B xong
edited = st.data_editor(pd.DataFrame([{
    "Xác nhận": t.status is TaskStatus.CONFIRMED, "Nhiệm vụ": t.title, "Môn": t.course,
    "Hạn nộp": t.deadline, "Giờ": t.estimated_hours, "Ưu tiên": t.priority.value,
    "Nguồn": t.source, "Tin cậy": f"{t.confidence:.0%}",
} for t in base_tasks]), hide_index=True, width="stretch", key="task_editor",
    disabled=["Nhiệm vụ", "Môn", "Hạn nộp", "Giờ", "Ưu tiên", "Nguồn", "Tin cậy"],
    column_config={"Hạn nộp": st.column_config.DatetimeColumn(format="DD/MM HH:mm")})
tasks = [replace(t, status=TaskStatus.CONFIRMED if ok else TaskStatus.PROPOSED)
         for t, ok in zip(base_tasks, edited["Xác nhận"])]
titles = {t.id: t.title for t in tasks}

# ---------------------------------------------------------------- 2. Thời khoá biểu
st.subheader("2. Thời khoá biểu")
upload = st.file_uploader("Tải CSV (cột: thu,bat_dau,ket_thuc,mon,phong)", type="csv")
sessions, tt_errors = load_timetable_csv(upload if upload else SAMPLE_DIR / "thoi_khoa_bieu.csv")
st.caption(("Đang dùng file bạn tải lên" if upload else "Đang dùng thời khoá biểu mẫu")
           + f" · {len(sessions)} buổi/tuần")
for err in tt_errors:
    st.warning(err)

# ---------------------------------------------------------------- 3. Cài đặt
st.subheader("3. Cài đặt")
c1, c2, c3, c4 = st.columns(4)
start = c1.date_input("Bắt đầu từ", value=date.today(), format="DD/MM/YYYY")
days = c2.slider("Số ngày", 7, 35, 21)
day_start, day_end = c3.slider("Khung giờ học", time(5), time(23, 59),
                               (time(7), time(22)), step=timedelta(minutes=30), format="HH:mm")
max_h = c4.number_input("Giờ tối đa/ngày", 0.5, 12.0, 4.0, step=0.5)
c1, c2 = st.columns([3, 1])
mode = c1.radio("Thuật toán", ["So sánh cả hai", *ALGORITHMS], horizontal=True,
                help="EDF: hạn gần nhất làm trước (baseline). CP-SAT: tối ưu ràng buộc (OR-Tools).")
min_block = c2.selectbox("Khối học tối thiểu", [30, 60, 90, 120], index=1,
                         format_func=lambda m: f"{m} phút",
                         help="CP-SAT không xếp khối ngắn hơn mức này (trừ việc cần ít giờ hơn).")

try:
    settings = ScheduleSettings(
        start=start, days=days, day_start=day_start, day_end=day_end, max_hours_per_day=max_h,
        min_block_minutes=min_block, not_before=datetime.now() if start <= date.today() else None)
except ValueError as e:
    st.error(f"Cài đặt không hợp lệ: {e}")
    st.stop()

if st.button("Xếp lịch", type="primary", key="run"):
    algos = ALGORITHMS if mode == "So sánh cả hai" else (mode,)
    with st.spinner("Đang xếp lịch..."):
        st.session_state.sched = {
            "results": {a: schedule(tasks, sessions, settings, a) for a in algos},
            "tasks": tasks, "sessions": sessions, "settings": settings}

run = st.session_state.get("sched")
if run and type(run["settings"]) is not ScheduleSettings:
    run = st.session_state.sched = None  # code vừa được nạp lại (khi phát triển): bỏ kết quả cũ
if not run:
    st.stop()
if not any(t.status is TaskStatus.CONFIRMED for t in run["tasks"]):
    st.info("Chưa có nhiệm vụ nào được xác nhận.")
    st.stop()
results, r_tasks, r_sessions, r_settings = (run[k] for k in ("results", "tasks", "sessions", "settings"))
r_titles = {t.id: t.title for t in r_tasks}

# ---------------------------------------------------------------- 4. Kết quả
st.subheader("4. Kết quả")
st.dataframe(pd.DataFrame([evaluate(r, r_tasks, r_sessions, r_settings)
                           for r in results.values()]).set_index("Thuật toán").T.astype(str),
             width="stretch")
shown = st.radio("Xem lịch của", list(results), horizontal=True) if len(results) > 1 \
    else next(iter(results))
result = results[shown]
for tid, h in result.missing_hours.items():
    st.warning(f"**{r_titles[tid]}** thiếu {h:g} giờ trước hạn nộp — không đủ thời gian rảnh.")

# Lịch tuần
weeks = sorted({d - timedelta(days=d.weekday()) for d in
                (r_settings.start + timedelta(days=i) for i in range(r_settings.days))})
week = st.select_slider("Tuần", weeks, format_func=lambda w: f"{w:%d/%m} – {w + timedelta(days=6):%d/%m}")
week_days = [week + timedelta(days=i) for i in range(7)]
day_label = {d: f"{WEEKDAY_VN[d.weekday()]} {d:%d/%m}" for d in week_days}


def _hour(dt: datetime) -> float:
    return dt.hour + dt.minute / 60


CLASS = "Lên lớp"
rows = [{"Ngày": day_label[b0.date()], "Từ": _hour(b0), "Đến": _hour(b1), "Màu": CLASS,
         "Nội dung": f"{s.course} ({s.room})" if s.room else s.course, "Giờ": f"{b0:%H:%M}–{b1:%H:%M}"}
        for b0, b1, s in busy_intervals(r_sessions, replace(r_settings, start=week, days=7,
                                                            not_before=None))]
rows += [{"Ngày": day_label[b.start.date()], "Từ": _hour(b.start), "Đến": _hour(b.end),
          "Màu": r_titles[b.task_id], "Nội dung": r_titles[b.task_id],
          "Giờ": f"{b.start:%H:%M}–{b.end:%H:%M}"}
         for b in result.blocks if b.start.date() in day_label]
if rows:
    df = pd.DataFrame(rows)
    df["Nhãn"] = df["Nội dung"].map(lambda s: s if len(s) <= 13 else s[:12] + "…")
    task_names = [r_titles[t.id] for t in r_tasks if t.id in {b.task_id for b in result.blocks}]
    palette = ["#4c78a8", "#f58518", "#54a24b", "#e45756", "#b279a2", "#eeca3b", "#72b7b2", "#ff9da6"]
    days_order = list(day_label.values())
    base = alt.Chart(df).encode(
        x=alt.X("Ngày:N", sort=days_order, scale=alt.Scale(domain=days_order),
                axis=alt.Axis(labelAngle=0, title=None, orient="top")),
        y=alt.Y("Từ:Q", scale=alt.Scale(domain=[day_start.hour, day_end.hour + 1], reverse=True,
                                        nice=False), title="Giờ"),
        tooltip=["Nội dung", "Ngày", "Giờ"])
    bars = base.mark_bar(cornerRadius=4).encode(
        y2="Đến:Q",
        color=alt.Color("Màu:N", title=None, legend=alt.Legend(orient="bottom", columns=2),
                        scale=alt.Scale(domain=[CLASS, *task_names],
                                        range=["#8a8f98", *palette[:len(task_names)]])))
    labels = base.mark_text(align="left", baseline="top", dx=-38, dy=3, fontSize=10,
                            color="white").encode(text="Nhãn:N")
    st.altair_chart((bars + labels).properties(height=560), width="stretch")
else:
    st.caption("Tuần này không có lịch.")

with st.expander("Danh sách khối học"):
    st.dataframe(pd.DataFrame([{
        "Ngày": f"{WEEKDAY_VN[b.start.weekday()]} {b.start:%d/%m}", "Từ": f"{b.start:%H:%M}",
        "Đến": f"{b.end:%H:%M}", "Nhiệm vụ": r_titles[b.task_id], "Giờ": round(b.hours, 1),
    } for b in result.blocks]), hide_index=True, width="stretch")

# ---------------------------------------------------------------- 5. Nhắc nhở
st.subheader("5. Nhắc nhở")
c1, c2 = st.columns(2)
before_block = c1.number_input("Nhắc trước khối học (phút)", 0, 240, 30, step=5)
before_deadline = c2.number_input("Nhắc trước hạn nộp (giờ)", 0, 168, 24)
reminders = make_reminders(result.blocks, r_tasks, before_block, before_deadline)

c1, c2 = st.columns(2)
c1.download_button("Tải lịch (.ics)", to_ics(result.blocks, r_tasks, before_block, before_deadline),
                   file_name="lich-hoc.ics", mime="text/calendar",
                   help="Mở file để nhập vào Google Calendar, Outlook hoặc lịch điện thoại.")
if c2.button("Lưu nhắc nhở cho lệnh gửi định kỳ"):
    save_reminders(reminders)
    c2.success(f"Đã lưu {len(reminders)} nhắc nhở. Chạy `python -m modules.scheduler.notify`.")

sender = TelegramSender.from_env()
if sender is None:
    st.info("Telegram chưa cấu hình: điền `TELEGRAM_BOT_TOKEN` (tạo bot với @BotFather) và "
            "`TELEGRAM_CHAT_ID` vào `.env`, rồi khởi động lại.", icon="💬")
else:
    c1, c2 = st.columns(2)
    try:
        if c1.button("Gửi tin thử"):
            sender(f"✅ Trợ lý AI học tập: kết nối Telegram thành công ({len(reminders)} nhắc nhở).")
            c1.success("Đã gửi.")
        if c2.button("Gửi nhắc nhở đến hạn"):
            sent = send_due(reminders, datetime.now(), sender)
            c2.success(f"Đã gửi {len(sent)} nhắc nhở.")
    except RuntimeError as e:
        st.error(str(e))

with st.expander(f"Danh sách nhắc nhở ({len(reminders)})"):
    for r in reminders:
        st.write(f"- `{r.remind_at:%d/%m %H:%M}` {r.message}")
