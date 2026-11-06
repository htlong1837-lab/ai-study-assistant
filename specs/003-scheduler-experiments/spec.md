# Feature Specification: Thí nghiệm so sánh EDF và CP-SAT

**Feature Branch**: `003-scheduler-experiments`

**Created**: 2026-11-06

**Status**: Draft

**Input**: "Thí nghiệm so sánh thuật toán cơ sở với thuật toán tối ưu trên nhiều bộ dữ liệu có mức tải khác nhau, tái lập được, xuất bảng và biểu đồ cho báo cáo SP2."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chạy lại thí nghiệm bằng một lệnh (Priority: P1)

Người chấm hoặc thành viên nhóm chạy một lệnh và nhận lại đúng các bảng, biểu đồ trong báo cáo.

**Independent Test**: Chạy lệnh hai lần, các chỉ số không phụ thuộc thời gian giống hệt nhau.

**Acceptance Scenarios**:

1. **Given** mã nguồn và thư viện đã cài, **When** chạy lệnh thí nghiệm,
   **Then** nhận file kết quả từng lần chạy, bảng tổng hợp và biểu đồ.
2. **Given** cùng hạt giống ngẫu nhiên, **When** chạy lại,
   **Then** dữ liệu sinh ra giống hệt; chỉ số chất lượng giống hệt với EDF và các ca CP-SAT đạt
   `OPTIMAL`. Ca CP-SAT dừng vì hết giờ (`FEASIBLE`) có thể lệch nhẹ do solver đa luồng — đã
   nêu trong báo cáo (C.5).

### User Story 2 - Đọc kết quả cho báo cáo (Priority: P1)

Người viết báo cáo có bảng trung bình ± độ lệch chuẩn theo từng kịch bản, số lần thắng/hòa/thua
giữa hai thuật toán, và biểu đồ.

### Edge Cases

- Thuật toán tối ưu hết giờ: ghi trạng thái để báo cáo nêu rõ.
- Kịch bản quá tải không thể làm đủ: chỉ số giờ thiếu phản ánh điều này, không lỗi.

## Requirements *(mandatory)*

- **FR-001**: Có ít nhất 3 kịch bản: nhẹ, vừa, quá tải; mỗi kịch bản ít nhất 10 bộ dữ liệu sinh ngẫu nhiên có hạt giống cố định.
- **FR-002**: Mỗi bộ dữ liệu ghi lại tỉ lệ tải (giờ cần làm / giờ có thể học trước hạn cuối).
- **FR-003**: Hai thuật toán chạy trên đúng cùng dữ liệu và cùng cài đặt; chỉ số tính bằng cùng một hàm.
- **FR-004**: Kết quả gồm: file từng lần chạy, bảng tổng hợp, thắng/hòa/thua, biểu đồ.
- **FR-005**: Bộ sinh dữ liệu có kiểm thử tự động.

## Success Criteria *(mandatory)*

- **SC-001**: Toàn bộ thí nghiệm chạy xong dưới 10 phút trên máy cá nhân.
- **SC-002**: Mọi lịch sinh ra có 0 xung đột ràng buộc cứng.
- **SC-003**: Bảng và biểu đồ dùng được trực tiếp trong báo cáo.

## Assumptions

- Dữ liệu tổng hợp (không phải nhiệm vụ thật của sinh viên) vì chưa có dữ liệu thật từ module B;
  báo cáo phải nêu rõ hạn chế này.
- Dùng thời khoá biểu mẫu trong repo, 28 ngày, khung 7h–22h, tối đa 4 giờ/ngày, khối tối thiểu 60 phút.
