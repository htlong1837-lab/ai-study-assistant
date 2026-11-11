# Sub-Plan 8: Tích hợp Toàn diện & Kịch bản Demo Vàng (Phase 9)

> **Mục tiêu:** Xây dựng fixture dữ liệu tích hợp, bài kiểm thử luồng đầu - cuối (End-to-End Integration Test), tài liệu hướng dẫn kịch bản demo `docs/module_b/DEMO.md` và hoàn thiện checklist bàn giao đồ án.  
> **Ước tính thời gian:** 5 giờ  
> **Phase tương ứng:** Phase 9

---

## 1. Kịch bản Demo Vàng (Golden Demo Scenario)

Kịch bản demo mô phỏng chính xác hành trình sử dụng thực tế của sinh viên, thể hiện sự phối hợp chặt chẽ giữa 4 module:

1. **Bước 1 (Giao bài ban đầu):**
   - Giảng viên gửi email `e-001` giao bài tập lớn kèm tài liệu PDF đính kèm: Hạn nộp ghi trong PDF là 18/11/2026 lúc 17:00, yêu cầu nộp file `.zip` lên hệ thống LMS.
   - Module D quét an toàn $\rightarrow$ Chuyển cho Module B.
   - Module B trích xuất, phát hiện không có mâu thuẫn $\rightarrow$ Đề xuất task `t-001` (trạng thái `proposed`).
   - Sinh viên xem thẻ đề xuất trên UI, kiểm tra đoạn trích dẫn nguyên văn, chỉnh sửa thời gian ước tính thành 8 giờ và bấm **"Xác nhận vào lịch"**.
   - Task `t-001` chuyển sang `confirmed` $\rightarrow$ Module C tự động xếp các khối tự học vào giờ rảnh trong tuần.
2. **Bước 2 (Giảng viên thông báo dời hạn & đổi kênh nộp):**
   - Vài ngày sau, giảng viên gửi email thứ hai `e-002`: *"Do hệ thống LMS bảo trì, deadline bài tập lớn được dời sang 23h59 ngày 25/11/2026 và các nhóm nộp qua link Google Drive"*.
   - Module D phân loại email là `assignment` và an toàn $\rightarrow$ Chuyển sang Module B.
3. **Bước 3 (Hệ thống phát hiện mâu thuẫn và sinh đề xuất cập nhật):**
   - Module B nhận diện email này tham chiếu đến task `t-001` đã tồn tại.
   - **Hệ thống không tự ý sửa lịch của sinh viên!** Thay vào đó, hệ thống sinh ra một `task_update_proposal` kèm cảnh báo lệch hạn nộp và đổi kênh nộp bài.
   - Gợi ý trên UI nghiêng về thông báo của email vì email được gửi sau và có tính chất gia hạn.
4. **Bước 4 (Sinh viên phê duyệt cập nhật & Module C điều chỉnh lịch):**
   - Sinh viên mở tab duyệt bài tập, thấy thông báo cảnh báo màu vàng cùng đề xuất dời hạn.
   - Sinh viên bấm **"Chấp nhận dời hạn"**.
   - Task `t-001` được cập nhật hạn mới vào CSDL.
   - Module C tự động tính toán lại lịch học quanh thời khóa biểu và đẩy thông báo nhắc nhở mới.

---

## 2. Nhiệm vụ chi tiết (Checklist)

- [ ] **T08.1 — Xây dựng fixtures kiểm thử tích hợp:**
  - Tạo `tests/extraction/fixtures/demo_scenario.py` chứa email ban đầu, file PDF mẫu, và email dời hạn.
- [ ] **T08.2 — Viết bài kiểm thử luồng đầu - cuối (`tests/extraction/test_e2e_flow.py`):**
  - Chạy toàn bộ 4 bước của kịch bản trên bằng `FakeLLMClient` và SQLite in-memory / file tạm.
  - Khẳng định tính đúng đắn của toàn bộ luồng:
    - Bắt đầu với task `proposed`.
    - Gọi `confirm()` thành `confirmed`.
    - Nhận email dời hạn tạo `update_proposal` (task gốc giữ nguyên).
    - Gọi `accept_update_proposal` thì hạn nộp mới được cập nhật.
    - Hàm `schedulable()` của Module C chỉ nhìn thấy task khi đã `confirmed`.
- [ ] **T08.3 — Soạn thảo `docs/module_b/DEMO.md`:**
  - Hướng dẫn từng bước thao tác trên giao diện Streamlit với dữ liệu giả định `core/mocks.py`.
  - Ảnh chụp màn hình minh họa các bước (lưu trong `docs/module_b/screens/`).
  - Hướng dẫn kiểm tra trên terminal bằng lệnh chạy demo.
- [ ] **T08.4 — Rà soát Checklist Định nghĩa Hoàn thành (Definition of Done):**
  - Kiểm tra toàn bộ 9 mục trong Mục 7 của Kế hoạch Master.

---

## 3. Tiêu chí nghiệm thu (Definition of Done)

- File kiểm thử `test_e2e_flow.py` chạy thành công 100% trong môi trường offline không có internet.
- Kịch bản demo trong `docs/module_b/DEMO.md` rõ ràng, ai trong nhóm cũng có thể tự chạy và trình diễn được trước giảng viên.
