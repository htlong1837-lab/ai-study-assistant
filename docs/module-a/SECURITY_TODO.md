# Security follow-up: verify and rotate any previously used API keys

## Kết quả rà soát ngày 09/11/2026

Người dùng xác nhận file `.env` cục bộ trước đây có key thật; hiện các biến key trong file đã để trống và key cũ đã được xóa/thu hồi trên Google AI Studio. `.env` không được track trong lịch sử Git local. Fixture trong lịch sử test dùng chuỗi tuần tự giả và người dùng xác nhận đó là dữ liệu giả; fixture hiện tại đã được thay bằng placeholder. Không có credential thật nào được xác định trong lịch sử Git local.

Key cũ trong `.env` đã được thu hồi và fixture lịch sử được xác nhận là dữ liệu giả. Không cần rewrite lịch sử cho fixture này. Key mới chỉ cần tạo khi ứng dụng cần dùng lại Gemini API.

---

## Các hành động bắt buộc dành cho Quản trị viên / Lập trình viên

1. **Nếu xác nhận key thật từng bị lộ, thu hồi trên Google AI Studio**:
   - Truy cập trang quản lý khóa: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
   - Tìm khóa có tiền tố / giá trị trùng khớp và nhấn **Delete / Revoke**.
   - Tạo khóa mới cho cá nhân sử dụng và không bao giờ commit vào repo.

2. **Đánh giá làm sạch lịch sử Git nếu key thật đã được commit**:
   - Nếu repository đã từng được push lên GitHub/GitLab hoặc chia sẻ ra bên ngoài, việc sửa code trong commit mới **không xóa được lịch sử cũ**.
   - Cần sử dụng công cụ như `git-filter-repo` hoặc `BFG Repo-Cleaner` để quét sạch toàn bộ chuỗi key khỏi lịch sử commit nếu dự án chuyển sang chế độ public.

3. **Nguyên tắc bảo mật hiện tại**:
   - Không commit API key; `.env` vẫn nằm ngoài Git.
   - Lời gọi QA đi qua `core/llm_client.py`; giao diện nhận key theo phiên và có thể dùng cấu hình host.
