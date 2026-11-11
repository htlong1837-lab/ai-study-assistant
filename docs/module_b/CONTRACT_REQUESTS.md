# Yêu cầu Điều chỉnh Hợp đồng Dữ liệu (Contract Change Requests)

> **Gửi**: Toàn thể nhóm phát triển đồ án `ai-study-assistant`  
> **Từ**: Module B — Trích xuất yêu cầu bài tập  
> **Nguyên tắc**: Không tự tiện sửa `core/contracts.py`. Ghi nhận đề xuất tại đây để thảo luận trong buổi họp nhóm.

---

## 1. Đề xuất CR-01: Bổ sung `thread_id` hoặc `in_reply_to` vào `ClassifiedEmail`

- **Hiện trạng**: `ClassifiedEmail` hiện chỉ có `id, sender, subject, body, received_at, label, safety, summary, attachments, label_confidence`.
- **Vấn đề**: Khi giảng viên gửi email đính chính dời hạn nộp (ví dụ: *"Re: [AI] Đề bài tập lớn"*), việc thiếu thông tin chuỗi hội thoại (`thread_id`) khiến hệ thống phải dựa hoàn toàn vào việc phân tích chuỗi tiêu đề và tên môn học để so khớp bài tập cũ.
- **Đề xuất**: Bổ sung trường `thread_id: str | None = None` vào `ClassifiedEmail`.
- **Phương án tạm thời của Module B**: Tạm thời sử dụng kết hợp tiêu đề, mã môn học và trường trích xuất `refers_to` để tìm bài tập tương ứng trong cơ sở dữ liệu.

---

## 2. Đề xuất CR-02: Cơ chế cho phép Đề xuất Nhiệm vụ chưa có Hạn nộp

- **Hiện trạng**: Dataclass `contracts.Task` có trường `deadline: datetime` bắt buộc (không cho phép `None`).
- **Vấn đề**: Khi thông báo của giảng viên quá mơ hồ (ví dụ: *"Nộp vào tuần sau"* nhưng chưa có thứ, hoặc chưa công bố hạn chót cụ thể), hệ thống theo nguyên tắc "không tự đoán mò" sẽ không thể gán deadline giả.
- **Phương án giải quyết của Module B**:
  - Trong cơ sở dữ liệu nội bộ của Module B (`db/schema.sql`), trường `deadline` của bảng `tasks` cho phép `NULL` khi nhiệm vụ ở trạng thái `proposed`.
  - Sinh viên sẽ xem đề xuất này trên giao diện và bắt buộc phải nhập hạn nộp thủ công (hoặc chờ email thông báo sau).
  - Khi sinh viên nhấn **"Xác nhận vào lịch"**, hệ thống kiểm tra nếu đã có deadline hợp lệ mới chuyển đổi sang `contracts.Task` để bàn giao cho Module C xếp lịch.

---

## 3. Đề xuất CR-03: Thống nhất Cấu hình Mốc bắt đầu Học kỳ (`SemesterConfig`)

- **Hiện trạng**: Một số bài tập có hạn nộp theo tuần học kỳ (ví dụ: *"Hết tuần 8 môn CSDL"*).
- **Vấn đề**: Để quy đổi tuần học kỳ thành ngày giờ tuyệt đối, hệ thống cần biết ngày bắt đầu tuần 1 của học kỳ.
- **Phương án giải quyết của Module B**: Cung cấp file cấu hình mẫu tại `config/semester.example.yaml` chứa `start_date` của học kỳ. Nếu chưa cấu hình, hệ thống sẽ đánh dấu cờ `UNRESOLVED` để sinh viên tự xác nhận trên UI.
