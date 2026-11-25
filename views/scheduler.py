from dataclasses import replace
from datetime import datetime, time, timedelta

import hashlib
import io

import altair as alt
import pandas as pd
import streamlit as st

from core import clock
from core import mocks
from core.contracts import TaskStatus
from db.repository import Repository
from modules.scheduler import ALGORITHMS, schedule
from modules.scheduler.metrics import evaluate
from modules.scheduler.model import WEEKDAY_VN, ScheduleSettings
from modules.scheduler.reminders import (
    TelegramSender, make_reminders, save_reminders, send_due, to_ics,
)
from modules.scheduler.slots import busy_intervals
from modules.scheduler.source import tasks_from_b
from core.llm_client import get_client
from modules.scheduler.timetable import load_timetable_csv
from modules.scheduler.timetable_image import (
    FIELDS as TT_FIELDS, TimetableImageError, gemini_generate, read_timetable_image,
    to_csv as tt_to_csv,
)
from modules.scheduler.progress import ProgressStore, block_key
from views import _account, _gemini, _planner, _timeline, _ui
from views._shared import module_header

module_header("📅 Lập lịch & nhắc nhở", "C")
ws = _account.current()

# ---------------------------------------------------------------- 1. Nhiệm vụ
st.subheader("1. Nhiệm vụ")
b_tasks, b_skipped = tasks_from_b(Repository(ws.db_path))
if b_tasks:
    base_tasks = b_tasks
    st.caption("AI chỉ đề xuất: chỉ nhiệm vụ được tích **Xác nhận** mới được xếp vào lịch. "
               f"Nguồn: {len(b_tasks)} nhiệm vụ từ trang Trích xuất "
               f"({sum(t.status is TaskStatus.CONFIRMED for t in b_tasks)} đã xác nhận).")
elif ws.is_guest:
    base_tasks = mocks.tasks()
    st.caption("AI chỉ đề xuất: chỉ nhiệm vụ được tích **Xác nhận** mới được xếp vào lịch. "
               "Chưa có nhiệm vụ nào từ trang Trích xuất, đang dùng dữ liệu mẫu.")
else:
    base_tasks = []
    st.info("Lịch của bạn chưa có nhiệm vụ nào. Lấy thư ở trang Hộp thư rồi trích xuất, hoặc dùng "
            "Thêm nhanh ngay dưới đây.", icon="🗂️")
for s in b_skipped:
    st.warning(f"Không xếp được “{s.title}” ({s.task_id}): {s.reason}")
_tt_courses, _ = load_timetable_csv(ws.timetable_source())
_planner.quick_add(Repository(ws.db_path), sorted({c.course for c in _tt_courses}), key="sched")
tasks = []
if base_tasks:
    edited = st.data_editor(pd.DataFrame([{
        "Xác nhận": t.status is TaskStatus.CONFIRMED, "Nhiệm vụ": t.title, "Môn": t.course,
        "Hạn nộp": t.deadline, "Giờ": t.estimated_hours, "Ưu tiên": t.priority.value,
        "Nguồn": t.source, "Tin cậy": f"{t.confidence:.0%}",
    } for t in base_tasks]), hide_index=True, width="stretch", key="task_editor",
        disabled=["Nhiệm vụ", "Môn", "Hạn nộp", "Giờ", "Ưu tiên", "Nguồn", "Tin cậy"],
        column_config={"Hạn nộp": st.column_config.DatetimeColumn(format="DD/MM HH:mm")})
    tasks = [replace(t, status=TaskStatus.CONFIRMED if ok else TaskStatus.PROPOSED)
             for t, ok in zip(base_tasks, edited["Xác nhận"])]
    if b_tasks:  # tích/bỏ tích Xác nhận được ghi vào CSDL của tài khoản, mở lại vẫn còn
        _repo = Repository(ws.db_path)
        for old, new in zip(base_tasks, tasks):
            if old.status is not new.status:
                _repo.set_task_status(new.id, "confirmed" if new.status is TaskStatus.CONFIRMED else "proposed")
titles = {t.id: t.title for t in tasks}

# ---------------------------------------------------------------- 2. Thời khoá biểu
def _timetable_from_image(upload) -> None:
    """Ảnh/PDF thời khoá biểu → Gemini đọc → bảng để sửa → lưu làm thời khoá biểu của người dùng."""
    data = upload.getvalue()
    sig = hashlib.sha256(data).hexdigest()
    with st.container(border=True):
        c_img, c_act = st.columns([1, 2], gap="medium")
        if upload.name.lower().endswith(".pdf"):
            c_img.markdown(f"📄 **{upload.name}**")
        else:
            try:
                c_img.image(data, width="stretch")
            except Exception:  # noqa: BLE001 — HEIC… trình duyệt không xem trước được
                c_img.markdown(f"🖼️ **{upload.name}**")
        with c_act:
            st.markdown("##### 📷 Chuyển ảnh thành thời khoá biểu")
            api_key = _gemini.key_input("tt_api_key", ws=ws)
            if st.button("Đọc thời khoá biểu bằng Gemini", type="primary", icon=":material/auto_awesome:",
                         disabled=not api_key, key="tt_read_image"):
                with st.spinner("Gemini đang đọc thời khoá biểu…"):
                    try:
                        rows, errs = read_timetable_image(
                            data, upload.name, gemini_generate(api_key, get_client().model))
                        st.session_state["tt_img"] = {"sig": sig, "rows": rows}
                    except TimetableImageError as exc:
                        st.error(str(exc), icon="⚠️")
        res = st.session_state.get("tt_img")
        if not res or res["sig"] != sig:
            return
        if not res["rows"]:
            st.info("Không tìm thấy buổi học nào trong ảnh. Thử ảnh rõ hơn, chụp thẳng cả bảng.", icon="🔍")
            return
        st.caption("Kiểm tra lại từng buổi: sửa trực tiếp trong bảng, thêm hoặc xoá dòng nếu cần. "
                   "Thứ: 2–7 hoặc CN; giờ dạng 07:00.")
        edited = st.data_editor(
            pd.DataFrame(res["rows"], columns=list(TT_FIELDS)), num_rows="dynamic", hide_index=True,
            width="stretch", key=f"tt_edit_{sig[:12]}",
            column_config={"thu": "Thứ", "bat_dau": "Bắt đầu", "ket_thuc": "Kết thúc", "mon": "Môn",
                           "phong": "Phòng"})
        rows = [{k: ("" if pd.isna(v) else str(v)) for k, v in r.items()} for r in edited.to_dict("records")]
        rows = [r for r in rows if any(r.values())]
        csv_text = tt_to_csv(rows)
        ok_sessions, errs = load_timetable_csv(io.StringIO(csv_text))
        for err in errs:
            st.warning(err)
        if st.button(f"💾 Lưu {len(ok_sessions)} buổi làm thời khoá biểu của tôi", key="tt_save_image",
                     disabled=not ok_sessions or bool(errs)):
            ws.save_timetable(csv_text.encode("utf-8"))
            st.session_state.pop("tt_img", None)
            st.toast("Đã lưu thời khoá biểu từ ảnh.", icon="🗓️")
            st.rerun()


st.subheader("2. Thời khoá biểu")
upload = st.file_uploader(
    "Tải thời khoá biểu: ảnh chụp, PDF hoặc CSV",
    type=["png", "jpg", "jpeg", "webp", "heic", "pdf", "csv"],
    help="Ảnh hoặc PDF: Gemini đọc và chuyển thành lịch, bạn xem lại và sửa trước khi lưu. "
         "CSV: các cột thu,bat_dau,ket_thuc,mon,phong.")
if upload is not None and not upload.name.lower().endswith(".csv"):
    _timetable_from_image(upload)
    upload = None  # lịch dùng để xếp là bản đã lưu, sau khi bạn duyệt kết quả đọc ảnh
if upload is not None:
    data = upload.getvalue()
    if data != (ws.timetable_path.read_bytes() if ws.has_own_timetable() else None):
        _check, _errs = load_timetable_csv(upload)
        if _check and not _errs:
            ws.save_timetable(data)  # lưu theo tài khoản: lần sau mở lại vẫn còn
            st.toast("Đã lưu thời khoá biểu của bạn.", icon="🗓️")
        upload.seek(0)
sessions, tt_errors = load_timetable_csv(upload if upload else ws.timetable_source())
c_tt, c_reset = st.columns([4, 1], vertical_alignment="center")
c_tt.caption(("Đang dùng thời khoá biểu của bạn" if (upload or ws.has_own_timetable())
              else "Đang dùng thời khoá biểu mẫu") + f" · {len(sessions)} buổi/tuần")
if ws.has_own_timetable() and not upload and c_reset.button("Dùng bản mẫu", key="tt_reset"):
    ws.reset_timetable()
    st.rerun()
for err in tt_errors:
    st.warning(err)

# ---------------------------------------------------------------- 3. Cài đặt
st.subheader("3. Cài đặt")
prefs = ws.read_state("schedule", {}) or {}  # cài đặt lần xếp trước của tài khoản


def _pref_time(name: str, default: time) -> time:
    try:
        return time.fromisoformat(prefs[name])
    except (KeyError, TypeError, ValueError):
        return default


MODES = ["So sánh cả hai", *ALGORITHMS]
BLOCKS = [30, 60, 90, 120]
c1, c2, c3, c4 = st.columns(4)
start = c1.date_input("Bắt đầu từ", value=clock.today(), format="DD/MM/YYYY")
days = c2.slider("Số ngày", 7, 35, int(prefs.get("days", 21)))
day_start, day_end = c3.slider("Khung giờ học", time(5), time(23, 59),
                               (_pref_time("day_start", time(7)), _pref_time("day_end", time(22))),
                               step=timedelta(minutes=30), format="HH:mm")
max_h = c4.number_input("Giờ tối đa/ngày", 0.5, 12.0, float(prefs.get("max_h", 4.0)), step=0.5)
c1, c2 = st.columns([3, 1])
ALGO_LABEL = {"EDF": "Nhanh", "CP-SAT": "Tối ưu"}
mode = c1.radio("Cách xếp", MODES, horizontal=True,
                index=MODES.index(prefs["mode"]) if prefs.get("mode") in MODES else 0,
                format_func=lambda a: ALGO_LABEL.get(a, a),
                help="Nhanh: việc có hạn gần nhất làm trước (EDF). "
                     "Tối ưu: cân giờ học giữa các ngày, hạn chế học khuya (CP-SAT).")
min_block = c2.selectbox("Khối học tối thiểu", BLOCKS,
                         index=BLOCKS.index(prefs["min_block"]) if prefs.get("min_block") in BLOCKS else 1,
                         format_func=lambda m: f"{m} phút",
                         help="Không chia nhỏ hơn mức này (trừ việc cần ít giờ hơn).")

try:
    settings = ScheduleSettings(
        start=start, days=days, day_start=day_start, day_end=day_end, max_hours_per_day=max_h,
        min_block_minutes=min_block, not_before=clock.now() if start <= clock.today() else None)
except ValueError as e:
    st.error(f"Cài đặt không hợp lệ: {e}")
    st.stop()

clicked = st.button("Xếp lịch", type="primary", key="run")
# Mở lại trang (hoặc phiên mới) sau khi đã từng xếp: tự xếp lại theo cài đặt đã lưu và dữ liệu mới nhất.
auto = "sched" not in st.session_state and prefs.get("ran") and bool(tasks)
if clicked or auto:
    if clicked:
        ws.write_state("schedule", {"days": days, "day_start": day_start.strftime("%H:%M"),
                                    "day_end": day_end.strftime("%H:%M"), "max_h": max_h, "mode": mode,
                                    "min_block": min_block, "ran": True})
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
                           for r in results.values()]).set_index("Thuật toán").T.astype(str)
             .rename(columns=lambda a: ALGO_LABEL.get(a, a)),
             width="stretch")
shown = st.radio("Xem lịch của", list(results), horizontal=True,
                 format_func=lambda a: ALGO_LABEL.get(a, a)) if len(results) > 1 \
    else next(iter(results))
result = results[shown]
r_deadline = {t.id: t.deadline for t in r_tasks}
for tid, h in result.missing_hours.items():
    if r_deadline[tid] <= clock.now():
        st.warning(f"**{r_titles[tid]}** đã quá hạn nộp ({r_deadline[tid]:%H:%M %d/%m}) — "
                   "không còn thời gian để xếp.", icon="⌛")
    else:
        st.warning(f"**{r_titles[tid]}** thiếu {h:g} giờ trước hạn nộp — không đủ thời gian rảnh.")

# Lịch tuần
weeks = sorted({d - timedelta(days=d.weekday()) for d in
                (r_settings.start + timedelta(days=i) for i in range(r_settings.days))})
week = st.select_slider("Tuần", weeks, format_func=lambda w: f"{w:%d/%m} – {w + timedelta(days=6):%d/%m}")
week_days = [week + timedelta(days=i) for i in range(7)]
day_label = {d: f"{WEEKDAY_VN[d.weekday()]} {d:%d/%m}" for d in week_days}

used_ids = [t.id for t in r_tasks if t.id in {b.task_id for b in result.blocks}]
task_color = _planner.task_colors(r_tasks)
progress = ProgressStore(ws.db_path)
done = progress.done()
default_day = clock.today() if clock.today() in week_days else week_days[0]
day = st.segmented_control(
    "Ngày", week_days, default=default_day, key=f"tl_day_{week}",
    format_func=lambda d: f"{WEEKDAY_VN[d.weekday()]} · {d:%d}") or default_day

col_tl, col_side = st.columns([3, 2], gap="large")
with col_side:
    day_blocks = [b for b in result.blocks if b.start.date() == day]
    if day_blocks:
        with st.container(border=True):
            st.markdown("##### ✅ Đánh dấu đã học")
            for b in day_blocks:
                k = block_key(b.task_id, b.start)
                ticked = st.checkbox(f"{b.start:%H:%M}–{b.end:%H:%M} · {r_titles[b.task_id]}",
                                     value=k in done, key=f"done_{k}")
                if ticked != (k in done):
                    done = progress.set_done(k, ticked)
                    if ticked and all(block_key(x.task_id, x.start) in done for x in day_blocks):
                        st.session_state["celebrate"] = True
                    st.rerun()
            n_done = sum(block_key(b.task_id, b.start) in done for b in day_blocks)
            st.progress(n_done / len(day_blocks), text=f"{n_done}/{len(day_blocks)} khối hôm nay")
    _ui.focus_timer()
with col_tl:
    items = _planner.day_items(day, result.blocks, r_tasks, r_sessions, r_settings, done, task_color)
    st.html(_timeline.render(items, clock.now()))
if st.session_state.pop("celebrate", False):
    _ui.confetti()
    st.toast("Xong hết các khối học trong ngày! 🎉", icon="🏆")


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
week_view = st.expander("Xem cả tuần")
if rows:
    df = pd.DataFrame(rows)
    df["Nhãn"] = df["Nội dung"].map(lambda s: s if len(s) <= 13 else s[:12] + "…")
    task_names = [r_titles[t.id] for t in r_tasks if t.id in {b.task_id for b in result.blocks}]
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
                                        range=[_timeline.CLASS_COLOR,
                                               *[task_color[t] for t in used_ids]])))
    labels = base.mark_text(align="left", baseline="top", dx=-38, dy=3, fontSize=10,
                            color="white").encode(text="Nhãn:N")
    week_view.altair_chart((bars + labels).properties(height=560), width="stretch")
else:
    week_view.caption("Tuần này không có lịch.")

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
    save_reminders(reminders, ws.reminders_path)
    c2.success(f"Đã lưu {len(reminders)} nhắc nhở. Nhắc nhở sẽ gửi qua Telegram khi dịch vụ nhắc đang chạy.")

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
            sent = send_due(reminders, clock.now(), sender)
            c2.success(f"Đã gửi {len(sent)} nhắc nhở.")
    except RuntimeError as e:
        st.error(str(e))

with st.expander(f"Danh sách nhắc nhở ({len(reminders)})"):
    for r in reminders:
        st.write(f"- `{r.remind_at:%d/%m %H:%M}` {r.message}")
