# Security Action Required: Revocation of Leaked API Keys

## Cảnh báo khẩn cấp (Security Advisory)

Trong phiên bản prototype trước đây của Module A, khóa API sau đã bị hardcode trong mã nguồn (`src/llm_client.py`) và lưu dưới dạng văn bản thuần trong file `.env`:

- **Key đã bị lộ**: `[REDACTED]` (Google AI / Gemini key)

---

## Các hành động bắt buộc dành cho Quản trị viên / Lập trình viên

1. **Thu hồi (Revoke) ngay lập tức trên Google AI Studio**:
   - Truy cập trang quản lý khóa: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
   - Tìm khóa có tiền tố / giá trị trùng khớp và nhấn **Delete / Revoke**.
   - Tạo khóa mới cho cá nhân sử dụng và không bao giờ commit vào repo.

2. **Làm sạch lịch sử Git (nếu dự án đã từng chia sẻ hoặc push lên remote)**:
   - Nếu repository đã từng được push lên GitHub/GitLab hoặc chia sẻ ra bên ngoài, việc sửa code trong commit mới **không xóa được lịch sử cũ**.
   - Cần sử dụng công cụ như `git-filter-repo` hoặc `BFG Repo-Cleaner` để quét sạch toàn bộ chuỗi key khỏi lịch sử commit nếu dự án chuyển sang chế độ public.

3. **Nguyên tắc bảo mật đã được áp dụng trong Module A từ Phase 0**:
   - Mã nguồn trong `src/` không sở hữu và không lưu trữ bất kỳ API key nào.
   - Ứng dụng hỗ trợ cơ chế BYOK (Bring Your Own Key) qua giao diện Streamlit theo từng phiên làm việc (`st.session_state`).
   - Mọi log và thông điệp lỗi đều qua hàm khử vết `mask_secrets()` để bảo vệ an toàn thông tin.
