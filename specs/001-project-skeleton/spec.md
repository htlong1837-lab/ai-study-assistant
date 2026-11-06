# Feature Specification: Khung dự án và hợp đồng dữ liệu chung

**Feature Branch**: `001-project-skeleton`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Dựng sườn dự án cho trợ lý AI học tập: một ứng dụng duy nhất có trang riêng cho 4 module (hỏi đáp tài liệu, trích xuất bài tập, lập lịch & nhắc nhở, email & bảo mật); chốt các cấu trúc dữ liệu trao đổi giữa module kèm dữ liệu giả để 4 người làm song song; một lớp gọi LLM dùng chung; ứng dụng chạy được trên máy lạ kể cả khi không có khóa API."

## User Scenarios & Testing *(mandatory)*

Người dùng của tính năng này có hai nhóm: **thành viên nhóm** (người phát triển 4 module) và
**người chấm/sinh viên dùng thử** (người mở ứng dụng để xem demo).

### User Story 1 - Mở ứng dụng trên máy mới (Priority: P1)

Một thành viên (hoặc giảng viên) tải mã nguồn về một máy chưa từng chạy dự án, làm theo hướng
dẫn cài đặt và mở được ứng dụng với trang chủ cùng 4 trang module, không cần khóa API nào.

**Why this priority**: Nếu không mở được ứng dụng thì không ai làm tiếp được và không có gì để
demo. Đây là điều kiện "xong tuần 1" trong kế hoạch nhóm.

**Independent Test**: Trên máy sạch, làm theo README, mở ứng dụng và đi qua đủ 5 trang mà không
gặp lỗi.

**Acceptance Scenarios**:

1. **Given** một máy chỉ có Python và mã nguồn, **When** người dùng làm theo README,
   **Then** ứng dụng mở trong trình duyệt và hiện trang chủ giới thiệu luồng xử lý.
2. **Given** ứng dụng đang chạy, **When** người dùng chọn lần lượt 4 trang module,
   **Then** mỗi trang hiện tên module, người phụ trách và trạng thái "đang phát triển".
3. **Given** không có khóa API nào được cấu hình, **When** người dùng mở ứng dụng,
   **Then** ứng dụng vẫn chạy và hiện thông báo rõ rằng chức năng AI đang tắt.

---

### User Story 2 - Làm module của mình bằng dữ liệu giả (Priority: P1)

Mỗi thành viên lấy được dữ liệu mẫu đúng định dạng do module đứng trước mình tạo ra (ví dụ
người làm lập lịch lấy được danh sách nhiệm vụ mẫu) mà không phải chờ module đó làm xong.

**Why this priority**: Kế hoạch làm song song chỉ khả thi khi định dạng trao đổi được chốt
và có dữ liệu giả; thiếu nó thì 3 người phải ngồi chờ.

**Independent Test**: Gọi bộ dữ liệu giả của từng cạnh nối trong luồng và kiểm tra dữ liệu
đúng định dạng, đúng các quy tắc chung.

**Acceptance Scenarios**:

1. **Given** định dạng dữ liệu đã chốt, **When** một module yêu cầu dữ liệu giả của module
   đứng trước, **Then** nhận được ít nhất 3 bản ghi hợp lệ cho mỗi loại dữ liệu.
2. **Given** dữ liệu giả về email, **When** kiểm tra trạng thái an toàn,
   **Then** có đủ cả ba trường hợp an toàn, nghi ngờ và độc để thử cổng chặn.
3. **Given** dữ liệu giả về nhiệm vụ, **When** kiểm tra trạng thái,
   **Then** có cả nhiệm vụ "đề xuất" và "đã xác nhận" kèm nguồn trích và độ tin cậy.
4. **Given** trang lập lịch, **When** mở trang, **Then** thấy danh sách nhiệm vụ mẫu
   lấy từ dữ liệu giả.

---

### User Story 3 - Gọi LLM qua một cửa chung (Priority: P2)

Thành viên làm module có AI gọi mô hình ngôn ngữ qua một cửa chung, cấu hình nhà cung cấp và
khóa ở một chỗ, được tự động lưu đệm câu trả lời lặp lại và đếm lượng sử dụng.

**Why this priority**: Cần cho module A, B, D và phần ước lượng giờ của C, nhưng các module
có thể bắt đầu phần không cần LLM trước.

**Independent Test**: Không có khóa thì nhận lỗi rõ ràng "chưa cấu hình"; có khóa thì gọi
cùng một câu hỏi hai lần và lần thứ hai lấy từ bộ đệm.

**Acceptance Scenarios**:

1. **Given** chưa cấu hình khóa, **When** một module gọi LLM,
   **Then** nhận thông báo lỗi rõ ràng mà ứng dụng không bị dừng.
2. **Given** đã cấu hình khóa, **When** gọi cùng một yêu cầu hai lần,
   **Then** lần thứ hai trả kết quả từ bộ đệm và không tính thêm lượng sử dụng.
3. **Given** đã có nhiều lần gọi, **When** xem thống kê,
   **Then** thấy tổng số lần gọi và lượng token đã dùng.

---

### Edge Cases

- Thiếu thư viện phụ thuộc: hướng dẫn cài đặt phải liệt kê đủ, ứng dụng báo lỗi rõ ràng.
- Một trang module ném lỗi: các trang khác vẫn dùng được.
- Nhiệm vụ không có hạn nộp hoặc độ tin cậy nằm ngoài khoảng 0–1: dữ liệu bị từ chối ngay
  khi tạo, không lọt vào module sau.
- Thời gian kết thúc của một khối học sớm hơn thời gian bắt đầu: dữ liệu bị từ chối.
- Bộ đệm LLM bị xoá hoặc hỏng: hệ thống gọi lại bình thường, không sập.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST có một ứng dụng duy nhất gồm trang chủ và 4 trang module
  (hỏi đáp tài liệu, trích xuất bài tập, lập lịch & nhắc nhở, email & bảo mật).
- **FR-002**: Trang chủ MUST mô tả luồng xử lý: email → kiểm tra an toàn → trích xuất →
  người dùng xác nhận → lập lịch → nhắc nhở, cùng nhánh hỏi đáp tài liệu.
- **FR-003**: Hệ thống MUST định nghĩa sáu loại dữ liệu trao đổi: email đã phân loại,
  tệp đính kèm an toàn, tài liệu đã đọc theo trang, nhiệm vụ, khối học, lời nhắc.
- **FR-004**: Mỗi loại dữ liệu MUST tự kiểm tra tính hợp lệ khi tạo (độ tin cậy 0–1, giờ kết
  thúc sau giờ bắt đầu, số trang dương, trạng thái thuộc danh sách cho phép).
- **FR-005**: Mọi kết quả do AI sinh ra MUST mang trạng thái "đề xuất" mặc định và có nguồn
  trích; chỉ nhiệm vụ "đã xác nhận" được đưa vào lịch.
- **FR-006**: Hệ thống MUST cung cấp hàm kiểm tra cổng chặn: email có trạng thái "độc" không
  bao giờ được chuyển tiếp.
- **FR-007**: Hệ thống MUST cung cấp dữ liệu giả cho từng loại dữ liệu, tối thiểu 3 bản ghi
  mỗi loại, phủ đủ các trạng thái.
- **FR-008**: Hệ thống MUST có một cửa gọi LLM dùng chung, đọc cấu hình từ biến môi trường,
  có bộ đệm theo nội dung yêu cầu và đếm số lần gọi, token.
- **FR-009**: Ứng dụng MUST chạy được khi không có khóa API; chức năng AI hiện trạng thái tắt.
- **FR-010**: Repo MUST có hướng dẫn cài đặt, danh sách thư viện, mẫu file cấu hình không
  chứa bí mật, và bộ kiểm thử tự động chạy được không cần mạng.
- **FR-011**: Repo MUST có thư mục và mẫu nhật ký sử dụng AI theo đúng các trường của đề bài.

### Key Entities

- **Email đã phân loại**: mã, người gửi, tiêu đề, nội dung, nhãn (thông báo bài tập, lịch
  học, thông báo chung, spam, lừa đảo, khác), tóm tắt, danh sách tệp đính kèm, trạng thái an toàn.
- **Tệp đính kèm an toàn**: đường dẫn, mã băm, email gốc; chỉ tồn tại khi đã qua cổng chặn.
- **Tài liệu đã đọc**: mã tài liệu, tên file, danh sách trang (số trang, văn bản).
- **Nhiệm vụ**: tên, môn, hạn nộp, số giờ ước tính, độ ưu tiên, nguồn trích, độ tin cậy,
  trạng thái (đề xuất / đã xác nhận / đã huỷ).
- **Khối học**: nhiệm vụ, giờ bắt đầu, giờ kết thúc.
- **Lời nhắc**: nhiệm vụ, thời điểm nhắc, kênh nhắc, nội dung.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Một thành viên trên máy mới mở được ứng dụng trong vòng 10 phút làm theo hướng dẫn.
- **SC-002**: 100% trang (5/5) mở được không lỗi khi không có khóa API.
- **SC-003**: Cả 4 thành viên bắt đầu viết module của mình trong cùng ngày nhận khung,
  không ai phải chờ dữ liệu thật của người khác.
- **SC-004**: Bộ kiểm thử tự động chạy xong dưới 30 giây và pass 100% khi không có mạng.
- **SC-005**: Gọi lặp lại cùng một yêu cầu LLM không phát sinh thêm chi phí.

## Assumptions

- Người dùng là sinh viên dùng ứng dụng trên máy tính cá nhân, một người dùng, chạy cục bộ;
  không cần đăng nhập.
- Định dạng dữ liệu lấy theo bảng "Giao tiếp giữa các module" trong kế hoạch nhóm ngày
  2026-10-27; bổ sung "Tệp đính kèm an toàn" thành loại riêng như bảng đã liệt kê.
- Cơ sở dữ liệu chung thuộc phần việc của module B; khung này chỉ tạo chỗ cấu hình đường dẫn,
  không thiết kế bảng.
- Nhà cung cấp LLM mặc định là Gemini (có hạn mức miễn phí); đổi nhà cung cấp bằng cấu hình.
- Giao diện tiếng Việt.
