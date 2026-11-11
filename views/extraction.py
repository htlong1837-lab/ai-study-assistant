from datetime import datetime, timezone
import streamlit as st

from core import config, mocks
from core.contracts import Priority, SafetyStatus, TaskStatus, can_forward
from core.llm_client import LLMClient, get_client
from db.repository import Repository
from modules.extraction import workflow
from views._shared import llm_status, module_header

# Khởi tạo Repository dùng chung
repo = Repository(config.DB_PATH)


def _seed_db_from_mocks_if_empty():
    """Nạp dữ liệu mẫu ban đầu từ core.mocks vào CSDL SQLite nếu bảng tasks trống."""
    existing = repo.list_tasks()
    if not existing:
        for t in mocks.tasks():
            repo.create_task({
                "id": t.id,
                "title": t.title,
                "course": t.course,
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "estimated_hours": t.estimated_hours,
                "priority": t.priority.value,
                "confidence": t.confidence,
                "status": t.status.value,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            repo.add_sources(t.id, [{
                "source": t.source,
                "field": "title",
                "quote": t.title,
                "kind": "mock",
            }])
            repo.save_assignment_details(t.id, {
                "raw_deadline_text": f"{t.deadline:%d/%m %H:%M}" if t.deadline else None,
                "submission_platform": "LMS Đại học Bách Khoa",
                "submission_format": [".pdf", ".zip"],
                "naming_convention": "MSSV_HoTen_BaiTap.zip",
                "grading_criteria": ["Đúng yêu cầu đề bài", "Báo cáo rõ ràng, mạch lạc"],
                "assumptions": ["Giờ mặc định là 23:59 nếu không ghi rõ"],
            })


_seed_db_from_mocks_if_empty()

module_header(
    "📝 Trích xuất bài tập",
    "Duy (B)",
    "ClassifiedEmail an toàn (từ D), ParsedDocument (từ A), Mocks",
    "Task trạng thái đề xuất → người dùng xác nhận",
)
llm_ready = llm_status()

# ---------------------------------------------------------------- 1. Cổng tiếp nhận Nguồn dữ liệu (Gate)
st.subheader("1. Nguồn dữ liệu đầu vào (Email & Tài liệu)")
st.caption("Cổng an toàn (Nguyên tắc II): Chỉ email an toàn mới được đưa vào phân tích. Email lừa đảo / độc hại bị chặn lập tức.")

c_email, c_doc = st.columns(2)

with c_email:
    st.markdown("##### 📧 Email từ Module D")
    for e in mocks.emails():
        is_safe = can_forward(e)
        if is_safe:
            st.success(f"**[AN TOÀN] {e.subject}**  \n*Từ:* `{e.sender}` — {e.summary or e.body[:60]}...")
        elif e.safety is SafetyStatus.SUSPICIOUS:
            st.warning(f"**[NGHI NGỜ] {e.subject}**  \n*Từ:* `{e.sender}` — {e.body[:60]}...")
        else:
            st.error(f"**[CHẶN - ĐỘC HẠI] {e.subject}**  \n*Từ:* `{e.sender}` (Đã chặn trước khi vào LLM)")

with c_doc:
    st.markdown("##### 📄 Tài liệu từ Module A")
    for doc in mocks.documents():
        st.info(f"**{doc.filename}** ({len(doc.pages)} trang)  \n*Nội dung:* {doc.pages[0].text[:80]}...")

# Nút kích hoạt trích xuất
if st.button("🚀 Bắt đầu trích xuất email & tài liệu mẫu vào DB", key="btn_run_extract"):
    client = get_client() if llm_ready else LLMClient(provider="fake", model="fake-model")
    with st.spinner("Đang trích xuất và chuẩn hóa bài tập..."):
        total_created = 0
        for e in mocks.emails():
            if can_forward(e):
                created = workflow.process_email(e, client, repo)
                total_created += len(created)
        for d in mocks.documents():
            created = workflow.process_document(d, client, repo)
            total_created += len(created)
        st.success(f"Đã xử lý xong! Tạo mới/cập nhật {total_created} bài tập trong cơ sở dữ liệu.")
        st.rerun()

# ---------------------------------------------------------------- 2. Cảnh báo Mâu thuẫn (Conflicts)
conflicts = [c for c in repo.list_conflicts() if not c.get("resolution")]
if conflicts:
    st.subheader("⚠️ Cảnh báo Mâu thuẫn giữa các Nguồn")
    for cf in conflicts:
        with st.warning(f"Phát hiện mâu thuẫn về **{cf['kind']}** cho Task `{cf['task_id']}`!"):
            st.write(f"- Nguồn A (`{cf.get('source_a')}`): **{cf.get('value_a')}**")
            st.write(f"- Nguồn B (`{cf.get('source_b')}`): **{cf.get('value_b')}**")
            if cf.get("suggestion"):
                st.info(f"💡 Gợi ý hệ thống: Nên ưu tiên phương án **{cf['suggestion'].upper()}** (nguồn cập nhật mới hơn).")

            col_a, col_b, col_m = st.columns(3)
            if col_a.button(f"Dùng giá trị A", key=f"cf_a_{cf['id']}"):
                workflow.resolve_conflict(cf["id"], choice="a", repo=repo)
                st.success("Đã áp dụng phương án A!")
                st.rerun()
            if col_b.button(f"Dùng giá trị B", key=f"cf_b_{cf['id']}"):
                workflow.resolve_conflict(cf["id"], choice="b", repo=repo)
                st.success("Đã áp dụng phương án B!")
                st.rerun()

# ---------------------------------------------------------------- 3. Đề xuất Dời hạn nộp (Update Proposals)
proposals = repo.list_pending_proposals()
if proposals:
    st.subheader("🔔 Đề xuất Dời hạn / Thay đổi Yêu cầu")
    for prop in proposals:
        with st.container(border=True):
            st.markdown(f"**Bài tập:** `{prop['task_id']}` | **Trường thay đổi:** `{prop['field']}`")
            st.write(f"- Giá trị cũ: `{prop.get('old_value')}`")
            st.write(f"- Giá trị đề xuất mới: **`{prop.get('new_value')}`**")
            if prop.get("quote"):
                st.caption(f"Trích dẫn: \"{prop['quote']}\" (từ `{prop.get('source')}`)")

            c_accept, c_reject = st.columns([1, 1])
            if c_accept.button("✅ Chấp nhận thay đổi", key=f"prop_acc_{prop['id']}"):
                workflow.accept_update_proposal(prop["id"], repo=repo)
                st.success("Đã cập nhật bài tập!")
                st.rerun()
            if c_reject.button("❌ Giữ nguyên hạn cũ", key=f"prop_rej_{prop['id']}"):
                workflow.reject_update_proposal(prop["id"], repo=repo)
                st.info("Đã từ chối đề xuất dời hạn.")
                st.rerun()

# ---------------------------------------------------------------- 4. Danh sách Đề xuất Chờ xác nhận (Proposed Tasks)
st.subheader("2. Đề xuất bài tập chờ sinh viên phê duyệt (Proposed Tasks)")
st.caption("Nguyên tắc I: AI chỉ đề xuất, người dùng quyết định. Chỉ bài tập được bấm **Xác nhận** mới được chuyển sang Module C lập lịch.")

proposed_tasks = repo.list_tasks(status="proposed")

if not proposed_tasks:
    st.info("Hiện không có bài tập nào đang chờ phê duyệt. Bạn có thể bấm 'Bắt đầu trích xuất' ở trên để nạp thêm.")
else:
    for t in proposed_tasks:
        tid = t["id"]
        conf_val = float(t.get("confidence", 1.0))
        conf_color = "green" if conf_val >= 0.85 else ("orange" if conf_val >= 0.60 else "red")

        with st.container(border=True):
            head_col, badge_col = st.columns([4, 1])
            head_col.markdown(f"#### 📌 {t['title']} — *{t.get('course') or 'Chung'}*")
            badge_col.markdown(f":{conf_color}[**Tin cậy {conf_val:.0%}**]")

            # Hiển thị hạn nộp
            raw_dl = t.get("deadline")
            dl_str = raw_dl.replace("T", " ")[:16] if raw_dl else "⚠️ Chưa rõ hạn nộp"
            st.write(f"📅 **Hạn nộp hiện tại:** `{dl_str}`")

            # Mở rộng xem chi tiết yêu cầu bài tập & tiêu chí chấm (US3 / T024)
            details = repo.get_assignment_details(tid)
            with st.expander("🔍 Chi tiết yêu cầu bài tập & Tiêu chí chấm điểm (Rubric)"):
                if details:
                    d1, d2 = st.columns(2)
                    d1.write(f"- **Kênh nộp:** {details.get('submission_platform') or 'Chưa rõ'}")
                    d1.write(f"- **Định dạng:** {details.get('submission_format') or 'Chưa rõ'}")
                    d2.write(f"- **Đặt tên file:** `{details.get('naming_convention') or 'Không yêu cầu'}`")
                    d2.write(f"- **Văn bản gốc:** *{details.get('raw_deadline_text') or 'Không rõ'}*")

                    criteria = details.get("grading_criteria")
                    if criteria:
                        st.markdown("**Tiêu chí chấm điểm (Rubric):**")
                        for crit in criteria:
                            st.write(f"  • {crit}")
                else:
                    st.write("Không có chi tiết bổ sung.")

            # Form chỉnh sửa inline (Mức 1 / T020)
            with st.expander("✏️ Chỉnh sửa thông tin trước khi duyệt"):
                c1, c2, c3 = st.columns(3)
                default_hours = float(t.get("estimated_hours") or 2.0)
                new_hours = c1.number_input("Số giờ làm (ước tính)", min_value=0.5, max_value=40.0, value=default_hours, step=0.5, key=f"h_{tid}")
                p_opts = ["low", "medium", "high"]
                curr_p = t.get("priority", "medium")
                p_idx = p_opts.index(curr_p) if curr_p in p_opts else 1
                new_priority = c2.selectbox("Mức ưu tiên", options=p_opts, index=p_idx, key=f"p_{tid}")
                new_deadline_input = c3.text_input("Ghi đè hạn nộp (YYYY-MM-DD HH:MM)", value=dl_str if "⚠️" not in dl_str else "", key=f"dl_{tid}")

            # Nút Xác nhận và Từ chối
            btn_col1, btn_col2, _ = st.columns([2, 2, 4])
            if btn_col1.button("✅ Xác nhận vào lịch", key=f"btn_confirm_{tid}", type="primary"):
                overrides = {
                    "estimated_hours": new_hours,
                    "priority": new_priority,
                }
                if new_deadline_input.strip():
                    try:
                        clean_dl = new_deadline_input.strip().replace(" ", "T")
                        if len(clean_dl) == 16:
                            clean_dl += ":00"
                        overrides["deadline"] = datetime.fromisoformat(clean_dl)
                    except Exception:
                        st.error("Định dạng hạn nộp không hợp lệ. Vui lòng nhập dạng YYYY-MM-DD HH:MM")
                        st.stop()
                try:
                    confirmed_task = workflow.confirm(tid, repo, overrides=overrides)
                    st.success(f"Đã xác nhận bài tập '{confirmed_task.title}' vào lịch học (Module C)!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Không thể xác nhận: {ex}")

            if btn_col2.button("🗑️ Từ chối đề xuất", key=f"btn_cancel_{tid}"):
                workflow.cancel(tid, repo)
                st.info(f"Đã từ chối đề xuất bài tập '{t['title']}'.")
                st.rerun()

# ---------------------------------------------------------------- 5. Danh sách Task Đã Xác nhận (Confirmed)
st.subheader("3. Bài tập đã xác nhận (Chuyển giao cho Module C)")
confirmed_tasks = repo.list_tasks(status="confirmed")
if confirmed_tasks:
    st.dataframe([
        {
            "Mã": t["id"],
            "Tên bài tập": t["title"],
            "Môn học": t.get("course"),
            "Hạn nộp": t.get("deadline", "")[:16],
            "Giờ làm": t.get("estimated_hours"),
            "Ưu tiên": t.get("priority"),
            "Độ tin cậy": f"{float(t.get('confidence', 1.0)):.0%}",
        }
        for t in confirmed_tasks
    ], use_container_width=True)
else:
    st.caption("Chưa có bài tập nào được xác nhận.")
