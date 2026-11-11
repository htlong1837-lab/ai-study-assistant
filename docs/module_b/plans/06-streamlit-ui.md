# Sub-Plan 6: Giao diện Người dùng Streamlit (FR-B05)

> **Mục tiêu:** Xây dựng màn hình tương tác người dùng tại `views/extraction.py` cho phép duyệt danh sách email/tài liệu an toàn, hiển thị thẻ đề xuất bài tập, cảnh báo mâu thuẫn, xem bằng chứng trích dẫn, chỉnh sửa inline và phê duyệt nhiệm vụ.  
> **Ước tính thời gian:** 4 giờ  
> **Phase tương ứng:** Phase 7

---

## 1. Thiết kế Giao diện theo Phân tầng (3 Levels)

### Mức 1 — Bắt buộc (MVP - Hoàn thành trước):
1. **Bộ chọn nguồn dữ liệu (Source Selector):**
   - Lọc danh sách email từ `mocks.emails()` hoặc DB: Chỉ hiển thị các email an toàn (`can_forward() == True`).
   - Hiển thị thông báo đỏ cảnh báo người dùng nếu email bị chặn vì độc hại (`SafetyStatus.MALICIOUS` / `SUSPICIOUS`).
2. **Thẻ Đề xuất Nhiệm vụ (Proposal Cards):**
   - Hiển thị danh sách các bài tập đang chờ duyệt (`status == 'proposed'`).
   - Thông tin hiển thị: Tên bài tập, Tên môn học, Hạn nộp đã chuẩn hóa kèm cụm từ nguyên văn trong văn bản gốc.
   - Danh sách các giả định chuẩn hóa (`assumptions`), ví dụ: *"Không ghi giờ, giả định 23:59"*.
3. **Form Chỉnh sửa Nhanh (Inline Edit):**
   - Cho phép người dùng chỉnh sửa trực tiếp: `Số giờ ước tính` (slider hoặc number input), `Độ ưu tiên` (Low / Medium / High), và chọn hạn nộp thủ công bằng date/time picker nếu hệ thống chưa nhận diện được.
4. **Nút Phê duyệt & Từ chối:**
   - Nút **"Xác nhận vào lịch"** (gọi `workflow.confirm()` $\rightarrow$ task chuyển sang `confirmed` sẵn sàng cho Module C).
   - Nút **"Từ chối"** (gọi `workflow.cancel()`).

### Mức 2 — Nên có (Trực quan hóa & Mâu thuẫn):
1. **Hộp cảnh báo mâu thuẫn (Conflict Warning Box):**
   - Khi có lệch hạn nộp giữa Email và PDF đề bài: Hiển thị `st.warning` với 3 nút lựa chọn:
     - `[Dùng hạn nộp từ Email]` (kèm nhãn *"Gợi ý của hệ thống"* nếu email mới hơn).
     - `[Dùng hạn nộp từ PDF]`.
     - `[Tự nhập hạn mới]`.
2. **Danh sách Đề xuất Cập nhật (Task Update Proposals):**
   - Hiển thị bảng các bài tập có email dời hạn: Hạn cũ $\rightarrow$ Hạn mới.
   - Nút `Chấp nhận thay đổi` hoặc `Giữ nguyên hạn cũ`.
3. **Cảnh báo Mơ hồ (Ambiguity Badges):**
   - Huy hiệu vàng cảnh báo thiếu thông tin (ví dụ: *"Chưa rõ kênh nộp bài - hãy hỏi lại giảng viên"*).

### Mức 3 — Nâng cao (Nếu còn thời gian):
1. **Trực quan hóa Độ tin cậy (Confidence Badges):**
   - Nhãn màu: Xanh lá ($\ge 0.85$), Vàng ($0.60 - 0.84$), Cam ($< 0.60$).
2. **Hộp thoại xem nguồn gốc (Source Evidence Dialog):**
   - Mở modal/expander xem lại toàn văn email hoặc trang PDF, tô sáng đoạn trích `evidence.quote`.

---

## 2. Nguyên tắc Kỹ thuật Streamlit

- **Không gọi LLM trong render loop:** Giao diện chỉ đọc và render dữ liệu từ SQLite DB. Lời gọi trích xuất chỉ kích hoạt khi người dùng bấm nút "Bắt đầu trích xuất" và được bọc trong `st.status` hoặc `st.spinner`.
- **Hỗ trợ chạy Offline:** Khi biến môi trường `B_USE_FAKE_LLM=1` hoặc chưa cấu hình API key, giao diện vẫn hoạt động trơn tru bằng Fake LLM client và dữ liệu giả `mocks.py`.
- **Quản lý Session State:** Dùng `st.session_state` để lưu trạng thái form chỉnh sửa inline, tránh mất dữ liệu khi Streamlit rerun trang.

---

## 3. Nhiệm vụ chi tiết (Checklist)

- [ ] **T06.1 — Cài đặt UI Mức 1 trong `views/extraction.py`:**
  - Tích hợp `llm_status()` và `module_header()` dùng chung.
  - Render danh sách nguồn an toàn từ `core/mocks.py` hoặc DB.
  - Render danh sách Proposed Tasks và form sửa inline.
  - Gắn sự kiện bấm nút Xác nhận / Từ chối gọi `workflow.py`.
- [ ] **T06.2 — Cài đặt UI Mức 2 & Mức 3:**
  - Thêm thành phần hiển thị mâu thuẫn và các nút giải quyết xung đột.
  - Thêm khu vực xem đề xuất cập nhật task (`task_update_proposals`).
- [ ] **T06.3 — Cập nhật và chạy kiểm thử `tests/test_pages.py`:**
  - Kiểm tra trang `views/extraction.py` render thành công, không gặp lỗi runtime khi mở trang.

---

## 4. Tiêu chí nghiệm thu (Definition of Done)

- Giao diện mở được trên trình duyệt, trực quan, hỗ trợ tiếng Việt đầy đủ.
- Luồng phê duyệt hoạt động: Bấm xác nhận chuyển trạng thái task từ `proposed` sang `confirmed` và phản ánh ngay trên trang Lập lịch (Module C).
- Chụp ảnh màn hình lưu vào `docs/module_b/screens/` phục vụ báo cáo SP2.
