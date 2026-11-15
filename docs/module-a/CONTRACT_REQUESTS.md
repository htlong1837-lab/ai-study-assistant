# Đề xuất thay đổi hợp đồng dùng chung

Hiện chưa yêu cầu sửa `core/contracts.py`. Reader giữ thông tin phụ (`selection_verified`, cảnh báo trang rỗng) trong model riêng Module A. Nếu Module B cần metadata này, thống nhất trường và vòng đời trước khi đề xuất contract chung.
