# Kiểm tra thủ công Module A

Mỗi dòng điền Pass/Fail và ghi chú sau khi chạy `streamlit run app.py`.

- [ ] Chrome: upload PDF có lớp chữ; đọc được từng trang; chưa nhập key vẫn đọc được.
- [ ] Bôi đen câu; popup thao tác xuất hiện; Giải thích/Đơn giản hóa/Dịch/Định nghĩa/Hỏi hoạt động.
- [ ] Nhập số trang rồi nhảy đúng trang; nút trang trước/sau, zoom và giao diện sáng/tối hoạt động.
- [ ] Hỏi tiếp trong cùng luồng giữ đoạn đã chọn và ngữ cảnh trước.
- [ ] Chọn lại đoạn đã hỏi mở luồng cũ.
- [ ] Bấm citation quay tới đúng trang và tô chọn evidence.
- [ ] Hỏi toàn tài liệu trả citation bấm được.
- [ ] Tải Markdown và kiểm tra nội dung hội thoại.
- [ ] File PDF sai magic bytes, quá lớn, quá 1000 trang hoặc scan được báo lỗi/cảnh báo rõ.
- [ ] PDF 2 cột, bảng, công thức, chọn qua trang, phóng to/thu nhỏ; ghi trình duyệt và phiên bản.
- [ ] Lặp lại các thao tác chính trên Edge và Firefox; ghi lỗi/cách tái hiện.
- [ ] PDF dài (300 trang) và PDF scan; ghi tốc độ, bộ nhớ quan sát được và cảnh báo hiển thị.
- [ ] Chạy xen kẽ QA với module khác, xóa key, đổi trang; không rò session state.

Điền Pass/Fail và ghi chú ngay sau mỗi mục. Đây là kiểm tra thủ công còn cần người dùng thực hiện; test Python không thay thế việc kiểm tra browser.
