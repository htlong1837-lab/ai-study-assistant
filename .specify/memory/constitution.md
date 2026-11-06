# Trợ lý AI học tập và lịch trình — Constitution

## Core Principles

### I. AI chỉ đề xuất, người dùng quyết định (NON-NEGOTIABLE)

- Mọi kết quả do mô hình AI tạo ra (nhãn email, nhiệm vụ trích xuất, câu trả lời, ước lượng giờ)
  MUST mang trạng thái `proposed` và kèm nguồn gốc (file, trang, email gốc) cùng độ tin cậy.
- Chỉ dữ liệu có trạng thái `confirmed` do người dùng xác nhận MUST được đưa vào lịch hoặc
  gửi nhắc nhở.
- Lý do: đề bài yêu cầu AI có vai trò rõ ràng nhưng nhóm chịu trách nhiệm về độ chính xác;
  một hạn nộp sai do AI đoán còn tệ hơn không có lịch.

### II. Chặn tại cổng

- Email, link, file đính kèm MUST đi qua module D (Email & bảo mật) trước khi tới A hoặc B.
- Nội dung có trạng thái an toàn `malicious` MUST NOT được chuyển sang module A hoặc B dưới
  bất kỳ hình thức nào; `suspicious` chỉ được chuyển khi người dùng chủ động cho phép.
- Lý do: hệ thống gửi nội dung cho LLM và mở file; nội dung độc không được lọt vào luồng.

### III. Hợp đồng dữ liệu chung, module độc lập

- Các module chỉ trao đổi với nhau qua dataclass trong `core/contracts.py`
  (`ClassifiedEmail`, `SafeAttachment`, `ParsedDocument`, `Task`, `StudyBlock`, `Reminder`).
- Mỗi hợp đồng MUST có dữ liệu giả (mock) tương ứng để mỗi module chạy và test được khi
  module bên cạnh chưa xong.
- Đổi một trường trong hợp đồng là thay đổi phá vỡ: MUST có pull request riêng, được cả 4
  thành viên đồng ý, và cập nhật mock cùng lúc.
- Lý do: 4 người làm song song 5 tuần; không ai được phải ngồi chờ người khác.

### IV. Có thể đo và có thể kiểm chứng

- Mỗi chức năng AI MUST có bộ dữ liệu đánh giá và chỉ số định lượng ghi trong kế hoạch
  (F1, độ chính xác trích dẫn, số hạn nộp kịp...) và MUST so sánh với một phương pháp
  cơ sở (baseline) đơn giản hơn.
- Logic không phụ thuộc LLM MUST có unit test chạy bằng `pytest` mà không cần mạng
  hay khóa API.
- Lý do: báo cáo SP2 bắt buộc có kiểm thử, đánh giá và lý do chọn phương pháp.

### V. Đơn giản, chạy được trên máy lạ

- Toàn bộ là Python; một ứng dụng Streamlit duy nhất, SQLite cục bộ; không tách backend,
  không Docker, không dịch vụ tự host.
- Ứng dụng MUST khởi động và demo được luồng lập lịch khi không có khóa API nào; chức năng
  cần LLM thì báo rõ là đang tắt thay vì sập.
- Chức năng ngoài phạm vi 5 tuần được ghi vào mục "Hướng phát triển" thay vì làm dở.
- Lý do: giảng viên chấm trên máy khác; luồng demo không được phụ thuộc vào mạng hay quota.

## Ràng buộc bảo mật và dữ liệu

- Khóa API chỉ nằm trong `.env` (không commit); repo có `.env.example` liệt kê tên biến.
- Không commit email thật, đề bài có thông tin cá nhân hay file `.db`; dữ liệu thật để trong
  `data/real/` (đã bị `.gitignore`) và phải ẩn danh trước khi gán nhãn.
- Mọi lời gọi LLM đi qua `core/llm_client.py` để cache, đếm token và chi phí ở một chỗ.

## Quy trình phát triển

- Mỗi tính năng bắt đầu bằng spec-kit: `/speckit-specify` → `/speckit-plan` →
  `/speckit-tasks` → `/speckit-implement`; tài liệu nằm trong `specs/NNN-ten-tinh-nang/`.
- Mỗi người làm trên nhánh riêng; merge vào `main` qua pull request do một thành viên khác
  review, để ai cũng giải thích được phần của người khác.
- `pytest` MUST pass trước khi merge.
- Mỗi phiên dùng chatbot AI cho đồ án MUST được ghi vào `ai-log/` ngay sau phiên (mã
  AI-xxx), gồm prompt, phản hồi đầy đủ và đánh giá của người dùng; cấm viết bù nhật ký.

## Governance

- Constitution này đứng trên mọi quy ước khác của repo. Spec và plan MUST có mục
  "Constitution Check" và giải thích mọi điểm vi phạm.
- Sửa đổi constitution qua pull request riêng, cả nhóm đồng ý; tăng phiên bản theo semver
  (MAJOR: bỏ/định nghĩa lại nguyên tắc; MINOR: thêm nguyên tắc/mục; PATCH: sửa câu chữ).
- Người review pull request kiểm tra tuân thủ nguyên tắc I–V.

**Version**: 1.0.0 | **Ratified**: 2026-11-06 | **Last Amended**: 2026-11-06
