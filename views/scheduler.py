import pandas as pd
import streamlit as st

from core import mocks
from core.contracts import schedulable
from views._shared import module_header

module_header("📅 Lập lịch & nhắc nhở", "Long (C)",
              "Task đã xác nhận (từ B), thời khoá biểu CSV",
              "StudyBlock, Reminder, file .ics")

tasks = mocks.tasks()
ready = {t.id for t in schedulable(tasks)}

st.subheader("Nhiệm vụ")
st.dataframe(pd.DataFrame([{
    "Xếp lịch": "✅" if t.id in ready else "⏳ chờ xác nhận",
    "Nhiệm vụ": t.title, "Môn": t.course,
    "Hạn nộp": t.deadline.strftime("%a %d/%m %H:%M"),
    "Giờ ước tính": t.estimated_hours, "Ưu tiên": t.priority.value,
    "Nguồn": t.source, "Độ tin cậy": f"{t.confidence:.0%}",
} for t in tasks]), hide_index=True, width="stretch")

titles = {t.id: t.title for t in tasks}
st.subheader("Lịch học (mẫu)")
st.dataframe(pd.DataFrame([{
    "Ngày": b.start.strftime("%a %d/%m"),
    "Từ": b.start.strftime("%H:%M"), "Đến": b.end.strftime("%H:%M"),
    "Nhiệm vụ": titles[b.task_id], "Số giờ": round(b.hours, 1),
} for b in mocks.study_blocks()]), hide_index=True, width="stretch")

st.subheader("Nhắc nhở (mẫu)")
for r in mocks.reminders():
    st.write(f"- `{r.remind_at:%d/%m %H:%M}` · {r.channel.value} · {r.message}")
