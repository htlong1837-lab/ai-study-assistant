from datetime import datetime
import streamlit as st

from core import mocks
from core.contracts import SafetyStatus, can_forward
from core.llm_client import get_client
from db.repository import Repository
from modules.extraction import workflow
from modules.extraction.intake import intake_from_d
from modules.extraction.rule_extractor import NoCacheRepository, RuleBasedLLM
from views import _account, _ui
from views._shared import llm_status, module_header

def _fmt_value(v):
    """Ngày giờ ISO → 'HH:MM dd/mm/yyyy'; giá trị khác giữ nguyên."""
    try:
        return datetime.fromisoformat(str(v)).strftime("%H:%M %d/%m/%Y")
    except (TypeError, ValueError):
        return v if v not in (None, "") else "—"


ws = _account.current()
repo = Repository(ws.db_path)

module_header(
    "📝 Trích xuất bài tập", "B")
llm_ready = llm_status()
if msg := st.session_state.pop("extract_flash", None):
    st.toast(msg, icon="📝")
# Khách thấy email mẫu để dùng thử; người đã đăng nhập chỉ thấy email của chính họ.
intake = (intake_from_d(st.session_state, mocks.emails, mocks.documents) if ws.is_guest
          else intake_from_d(st.session_state, list, list))

# ---------------------------------------------------------------- 1. Cổng tiếp nhận Nguồn dữ liệu (Gate)
st.subheader("1. Nguồn dữ liệu đầu vào (Email & Tài liệu)")
st.caption("🔒 Chỉ email đã qua kiểm tra an toàn mới được phân tích; email lừa đảo hoặc độc hại đã bị chặn từ trước.")

c_email, c_doc = st.columns(2)

with c_email:
    st.markdown("##### 📧 Email đã qua kiểm tra")
    if intake.from_d:
        st.caption(f"{len(intake.emails)} email đã duyệt ở trang Hộp thư.")
    else:
        st.caption("Chưa có email nào được chuyển từ trang Hộp thư, đang dùng dữ liệu mẫu.")
    for e in intake.emails:
        is_safe = can_forward(e, allow_suspicious=intake.allow_suspicious(e))
        if is_safe and e.safety is SafetyStatus.SUSPICIOUS:
            st.warning(f"**[NGHI NGỜ – ĐÃ DUYỆT] {e.subject}**  \n*Từ:* `{e.sender}` — {e.summary or e.body[:60]}...")
        elif is_safe:
            st.success(f"**[AN TOÀN] {e.subject}**  \n*Từ:* `{e.sender}` — {e.summary or e.body[:60]}...")
        elif e.safety is SafetyStatus.SUSPICIOUS:
            st.warning(f"**[NGHI NGỜ] {e.subject}**  \n*Từ:* `{e.sender}` — {e.body[:60]}...")
        else:
            st.error(f"**[CHẶN - ĐỘC HẠI] {e.subject}**  \n*Từ:* `{e.sender}` (Đã chặn trước khi vào LLM)")

with c_doc:
    st.markdown("##### 📄 Tài liệu đính kèm")
    if intake.from_d and not intake.documents:
        st.caption("Email đã duyệt không có tệp đính kèm đọc được.")
    for doc in intake.documents:
        st.info(f"**{_ui.file_label(doc.filename)}** ({len(doc.pages)} trang)  \n*Nội dung:* {doc.pages[0].text[:80]}...")

# Nút kích hoạt trích xuất & Demo
c_act1, c_act2 = st.columns(2)
with c_act1:
    if not llm_ready:
        st.caption("🧩 Chưa có khóa AI: dùng bộ trích xuất theo luật (đọc hạn nộp, tên bài, định dạng, "
                   "tiêu chí chấm). Độ phủ thấp hơn LLM; câu trích vẫn được kiểm chứng như thường.")
    if st.button("🚀 Bắt đầu trích xuất email & tài liệu vào DB", key="btn_run_extract", type="primary"):
        if llm_ready:
            client, work_repo = get_client(), repo
        else:
            client, work_repo = RuleBasedLLM(), NoCacheRepository(repo)
        with st.spinner("Đang trích xuất và chuẩn hóa bài tập..."):
            touched: set[str] = set()
            for e in intake.emails:
                allow = intake.allow_suspicious(e)
                if can_forward(e, allow_suspicious=allow):
                    touched |= set(workflow.process_email(e, client, work_repo, allow_suspicious=allow))
            for d in intake.documents:
                touched |= set(workflow.process_document(d, client, work_repo,
                                                         linked_email=intake.linked_email(d)))
        st.session_state["extract_flash"] = (
            f"Đã xử lý xong: {len(touched)} bài tập được tạo hoặc cập nhật." if touched
            else "Không tìm thấy bài tập nào có hạn nộp trong các nguồn này.")
        st.rerun()

with c_act2:
    if st.button("⚡ Tạo tình huống mâu thuẫn mẫu để demo", key="btn_demo_conflict"):
        repo.add_conflict({
            "task_id": "t-004",
            "kind": "deadline",
            "value_a": "2026-11-20T23:59:00",
            "source_a": "email:e-001",
            "value_b": "2026-11-27T23:59:00",
            "source_b": "doc:de_bai_ai.pdf#p1",
            "suggestion": "b",
        })
        st.warning("Đã tạo tình huống mâu thuẫn hạn nộp mẫu (Email vs PDF) để kiểm thử!")
        st.rerun()

# ---------------------------------------------------------------- 2. Cảnh báo Mâu thuẫn (Conflicts)
conflicts = [c for c in repo.list_conflicts() if not c.get("resolution")]
if conflicts:
    st.subheader("⚠️ Cảnh báo Mâu thuẫn giữa các Nguồn")
    for cf in conflicts:
        with st.warning(f"Phát hiện mâu thuẫn về **{cf['kind']}** cho nhiệm vụ **{(repo.get_task(cf['task_id']) or {}).get('title', cf['task_id'])}**!"):
            st.write(f"- Nguồn A (`{cf.get('source_a')}`): **{cf.get('value_a')}**")
            st.write(f"- Nguồn B (`{cf.get('source_b')}`): **{cf.get('value_b')}**")
            if cf.get("suggestion"):
                st.info(f"💡 Gợi ý hệ thống: Nên ưu tiên phương án **{cf['suggestion'].upper()}** (nguồn cập nhật mới hơn).")

            col_a, col_b, col_m = st.columns(3)
            if col_a.button("Dùng giá trị A", key=f"cf_a_{cf['id']}"):
                workflow.resolve_conflict(cf["id"], choice="a", repo=repo)
                st.success("Đã áp dụng phương án A!")
                st.rerun()
            if col_b.button("Dùng giá trị B", key=f"cf_b_{cf['id']}"):
                workflow.resolve_conflict(cf["id"], choice="b", repo=repo)
                st.success("Đã áp dụng phương án B!")
                st.rerun()

# ---------------------------------------------------------------- 3. Đề xuất Dời hạn nộp (Update Proposals)
proposals = repo.list_pending_proposals()
if proposals:
    st.subheader("🔔 Đề xuất Dời hạn / Thay đổi Yêu cầu")
    for prop in proposals:
        with st.container(border=True):
            task_row = repo.get_task(prop["task_id"]) or {}
            field_vn = {"deadline": "Hạn nộp"}.get(prop["field"], prop["field"])
            st.markdown(f"**{task_row.get('title', prop['task_id'])}** · {field_vn}")
            st.markdown(f"~~{_fmt_value(prop.get('old_value'))}~~ → **{_fmt_value(prop.get('new_value'))}**")
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
st.subheader("2. Chờ bạn duyệt")
st.caption("AI chỉ gợi ý, bạn là người quyết định. Chỉ bài tập bạn bấm **Xác nhận** mới được đưa vào lịch học.")

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

            # Xem bằng chứng trích dẫn nguyên văn (Evidence Grounding)
            sources = repo.get_sources(tid)
            if sources:
                with st.expander(f"📎 Bằng chứng trích dẫn nguồn ({len(sources)} nguồn)"):
                    for s in sources:
                        f_name = s.get("field") or "nhiệm vụ"
                        st.markdown(f"- **Trường `{f_name}`** (từ `{s.get('source')}`):")
                        if s.get("quote"):
                            st.caption(f'> ❝ *{s["quote"]}* ❞')

            # Form chỉnh sửa inline (Mức 1 / T020)
            with st.expander("✏️ Chỉnh sửa thông tin trước khi duyệt"):
                c1, c2, c3 = st.columns(3)
                default_hours = float(t.get("estimated_hours") or 2.0)
                new_hours = c1.number_input("Số giờ làm (ước tính)", min_value=0.5, max_value=40.0, value=default_hours, step=0.5, key=f"h_{tid}")
                p_opts = ["low", "medium", "high"]
                curr_p = t.get("priority", "medium")
                p_idx = p_opts.index(curr_p) if curr_p in p_opts else 1
                new_priority = c2.selectbox("Mức ưu tiên", options=p_opts, index=p_idx, key=f"p_{tid}")
                new_deadline_input = c3.text_input("Ghi đè hạn nộp (YYYY-MM-DD HH:MM)", value=dl_str if "⚠️" not in dl_str else "",
                                                   # khoá gắn với hạn hiện tại: khi hạn đổi (chấp nhận dời hạn) ô được làm mới
                                                   key=f"dl_{tid}_{t.get('deadline')}")

            # Nút Xác nhận và Từ chối
            btn_col1, btn_col2, _ = st.columns([2, 2, 4])
            if btn_col1.button("✅ Xác nhận vào lịch", key=f"btn_confirm_{tid}", type="primary"):
                overrides = {
                    "estimated_hours": new_hours,
                    "priority": new_priority,
                }
                if new_deadline_input.strip() and new_deadline_input.strip() != dl_str:  # chỉ ghi khi người dùng sửa
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
                    st.success(f"Đã xác nhận bài tập '{confirmed_task.title}' vào lịch học!")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Không thể xác nhận: {ex}")

            if btn_col2.button("🗑️ Từ chối đề xuất", key=f"btn_cancel_{tid}"):
                workflow.cancel(tid, repo)
                st.info(f"Đã từ chối đề xuất bài tập '{t['title']}'.")
                st.rerun()

# ---------------------------------------------------------------- 5. Danh sách Task Đã Xác nhận (Confirmed)
st.subheader("3. Đã xác nhận")
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
    ], width="stretch")
else:
    st.caption("Chưa có bài tập nào được xác nhận.")
