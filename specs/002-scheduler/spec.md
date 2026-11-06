# Feature Specification: Lập lịch học và nhắc nhở (Module C)

**Feature Branch**: `002-scheduler`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Module C: nhận các nhiệm vụ đã được sinh viên xác nhận (tên, hạn nộp, số giờ ước tính, độ ưu tiên) và thời khoá biểu, tự xếp các khối học vào thời gian rảnh sao cho kịp hạn, không quá số giờ tối đa mỗi ngày, tải đều giữa các ngày. Có thuật toán cơ sở 'hạn gần nhất làm trước' để so sánh với thuật toán tối ưu ràng buộc. Tạo nhắc nhở trước mỗi khối học và trước hạn nộp, xuất file lịch và gửi qua Telegram. Giao diện lịch tuần."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Xếp lịch học tự động (Priority: P1) 🎯 MVP

Sinh viên đã xác nhận một số nhiệm vụ và nhập thời khoá biểu. Họ chọn khoảng thời gian, giờ học
tối đa mỗi ngày, khung giờ học được (ví dụ 7h–22h), rồi bấm xếp lịch. Hệ thống đưa ra các khối
học cụ thể (ngày, giờ bắt đầu, giờ kết thúc, nhiệm vụ) không trùng giờ lên lớp.

**Why this priority**: Đây là giá trị cốt lõi của module và là điểm cuối của luồng email → lịch.

**Independent Test**: Dùng nhiệm vụ mẫu và thời khoá biểu mẫu, bấm xếp lịch, kiểm tra mọi khối
học nằm trong giờ rảnh, trước hạn nộp và không vượt giờ tối đa mỗi ngày.

**Acceptance Scenarios**:

1. **Given** 3 nhiệm vụ đã xác nhận đủ thời gian để làm, **When** xếp lịch,
   **Then** mỗi nhiệm vụ được xếp đủ số giờ ước tính, toàn bộ trước hạn nộp.
2. **Given** thời khoá biểu có giờ lên lớp, **When** xếp lịch,
   **Then** không có khối học nào trùng giờ lên lớp.
3. **Given** giới hạn 4 giờ/ngày, **When** xếp lịch,
   **Then** không ngày nào có quá 4 giờ học.
4. **Given** một nhiệm vụ còn ở trạng thái "đề xuất", **When** xếp lịch,
   **Then** nhiệm vụ đó không xuất hiện trong lịch.
5. **Given** tổng số giờ cần làm vượt quá thời gian rảnh trước hạn, **When** xếp lịch,
   **Then** hệ thống vẫn trả lịch tốt nhất có thể và chỉ rõ nhiệm vụ nào thiếu bao nhiêu giờ;
   nhiệm vụ ưu tiên cao được đảm bảo trước.

---

### User Story 2 - So sánh hai thuật toán (Priority: P1)

Sinh viên (và người chấm) chọn thuật toán cơ sở hoặc thuật toán tối ưu, hoặc chạy cả hai, và
xem bảng chỉ số: số nhiệm vụ kịp hạn, số giờ thiếu, số xung đột, độ đều tải theo ngày, số lần
chuyển việc, thời gian chạy.

**Why this priority**: Báo cáo SP2 bắt buộc so sánh với phương pháp cơ sở và giải thích lý do chọn.

**Independent Test**: Chạy cả hai trên cùng dữ liệu, nhận hai bảng chỉ số cùng định nghĩa.

**Acceptance Scenarios**:

1. **Given** cùng dữ liệu đầu vào, **When** chạy cả hai thuật toán,
   **Then** hiện bảng chỉ số đặt cạnh nhau cho cả hai.
2. **Given** dữ liệu quá tải, **When** so sánh,
   **Then** thuật toán tối ưu không bỏ sót nhiệm vụ ưu tiên cao nhiều hơn thuật toán cơ sở.

---

### User Story 3 - Nhắc nhở (Priority: P2)

Sinh viên nhận nhắc nhở trước mỗi khối học (mặc định 30 phút) và trước hạn nộp (mặc định 24 giờ):
tải về file lịch để nhập vào ứng dụng lịch trên điện thoại, hoặc nhận tin nhắn Telegram.

**Why this priority**: Kế hoạch yêu cầu nhắc nhở; nhưng lịch đã có giá trị kể cả khi chưa nhắc.

**Independent Test**: Tạo file lịch từ lịch mẫu và nhập vào một ứng dụng lịch; gửi một tin thử
qua Telegram khi đã cấu hình.

**Acceptance Scenarios**:

1. **Given** một lịch đã xếp, **When** tải file lịch,
   **Then** file chứa mọi khối học và mốc hạn nộp, mỗi sự kiện có báo trước theo cài đặt.
2. **Given** chưa cấu hình Telegram, **When** mở phần nhắc nhở,
   **Then** nút gửi bị tắt và có hướng dẫn cấu hình; ứng dụng không lỗi.
3. **Given** đã cấu hình Telegram và có nhắc nhở đến hạn, **When** chạy gửi nhắc nhở,
   **Then** mỗi nhắc nhở đến hạn được gửi đúng một lần.

---

### User Story 4 - Xem lịch tuần (Priority: P2)

Sinh viên xem lịch dạng tuần: các cột là ngày, trục dọc là giờ, thấy cả giờ lên lớp và khối học,
màu theo nhiệm vụ; chuyển tuần trước/sau.

**Independent Test**: Mở trang lịch với dữ liệu mẫu, thấy đúng các khối ở đúng ngày giờ.

**Acceptance Scenarios**:

1. **Given** lịch đã xếp, **When** xem tuần hiện tại, **Then** thấy khối học và giờ lên lớp
   phân biệt được bằng màu, kèm tên nhiệm vụ khi rê chuột.

### Edge Cases

- Không có nhiệm vụ nào đã xác nhận: hiện thông báo, không chạy thuật toán.
- Hạn nộp đã qua hoặc trước thời điểm bắt đầu xếp: nhiệm vụ được báo "không thể xếp".
- File thời khoá biểu sai cột, sai giờ: báo dòng lỗi, bỏ qua dòng đó, không sập.
- Thuật toán tối ưu chạy quá giới hạn thời gian: trả lời giải tốt nhất tìm được và ghi rõ là
  chưa chứng minh tối ưu.
- Giờ ước tính không chia hết cho đơn vị thời gian: làm tròn lên.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST chỉ xếp lịch cho nhiệm vụ trạng thái "đã xác nhận".
- **FR-002**: Hệ thống MUST nhập thời khoá biểu hằng tuần từ file CSV (thứ, giờ bắt đầu, giờ kết thúc, môn, phòng).
- **FR-003**: Người dùng MUST đặt được: ngày bắt đầu, số ngày xếp, khung giờ học mỗi ngày, số giờ học tối đa mỗi ngày.
- **FR-004**: Khối học MUST không trùng giờ lên lớp, không trùng nhau, nằm trong khung giờ học, kết thúc trước hạn nộp của nhiệm vụ.
- **FR-005**: Hệ thống MUST cung cấp thuật toán cơ sở "hạn gần nhất làm trước" và thuật toán tối ưu ràng buộc trên cùng đầu vào, đầu ra.
- **FR-006**: Thuật toán tối ưu MUST ưu tiên theo thứ tự: (1) không thiếu giờ, có trọng số theo độ ưu tiên; (2) tải đều giữa các ngày; (3) ít lần chuyển việc vụn vặt.
- **FR-007**: Khi không đủ thời gian, hệ thống MUST trả lịch một phần kèm số giờ thiếu của từng nhiệm vụ.
- **FR-008**: Hệ thống MUST tính chỉ số: nhiệm vụ kịp hạn, giờ thiếu, xung đột, độ lệch tải theo ngày, số khối học, thời gian chạy.
- **FR-009**: Hệ thống MUST tạo nhắc nhở trước mỗi khối học và trước hạn nộp, thời gian báo trước chỉnh được.
- **FR-010**: Hệ thống MUST xuất file lịch chuẩn iCalendar.
- **FR-011**: Hệ thống MUST gửi được nhắc nhở qua Telegram khi đã cấu hình, mỗi nhắc nhở tối đa một lần.
- **FR-012**: Giao diện MUST hiện lịch tuần gồm giờ lên lớp và khối học.

### Key Entities

- **Thời khoá biểu**: các buổi lên lớp lặp lại hằng tuần (thứ, giờ bắt đầu, giờ kết thúc, môn, phòng).
- **Cài đặt xếp lịch**: ngày bắt đầu, số ngày, khung giờ học, giờ tối đa mỗi ngày, độ dài đơn vị thời gian.
- **Kết quả xếp lịch**: danh sách khối học, giờ thiếu của từng nhiệm vụ, chỉ số, tên thuật toán, trạng thái lời giải.
- Dùng lại `Task`, `StudyBlock`, `Reminder` từ hợp đồng chung.

## Success Criteria *(mandatory)*

- **SC-001**: Với dữ liệu đủ thời gian, 100% nhiệm vụ đã xác nhận được xếp đủ giờ và kịp hạn.
- **SC-002**: 0 xung đột với giờ lên lớp trong mọi trường hợp thử.
- **SC-003**: Xếp lịch 4 tuần với 15 nhiệm vụ cho kết quả trong dưới 10 giây.
- **SC-004**: Trên dữ liệu quá tải, thuật toán tối ưu có tổng giờ thiếu (có trọng số ưu tiên) không cao hơn thuật toán cơ sở.
- **SC-005**: File lịch xuất ra nhập được vào Google Calendar mà không báo lỗi.

## Assumptions

- Thời gian theo giờ địa phương của máy, một múi giờ.
- Đơn vị thời gian mặc định 30 phút; khung giờ học mặc định 7h–22h; tối đa 4 giờ/ngày.
- Số giờ ước tính do module B cung cấp (bắt buộc trong hợp đồng `Task`), C không tự ước lượng.
- Không đồng bộ hai chiều với Google Calendar (đã cắt khỏi phạm vi); xuất file là đủ.
- Gửi Telegram chạy khi người dùng bấm nút hoặc chạy lệnh định kỳ; không có tiến trình nền luôn chạy.
