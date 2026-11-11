# Feature Specification: Trích xuất yêu cầu bài tập từ email và văn bản (Module B)

**Feature Branch**: `004-assignment-extraction`

**Created**: 2026-11-08

**Status**: Draft

**Input**: User description: "Xây dựng Module B Trích xuất yêu cầu bài tập từ email/văn bản đầu vào, trích xuất các thông tin như tiêu đề, hạn nộp và nội dung chi tiết."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tự động trích xuất bài tập từ email thông báo và đề bài (Priority: P1)

Sinh viên nhận được email thông báo bài tập từ giảng viên (kèm hoặc không kèm tài liệu đề bài). Hệ thống tự động phân tích nội dung, trích xuất các thông tin cốt lõi gồm: tên bài tập, môn học, hạn nộp và hiển thị dưới dạng đề xuất nhiệm vụ (proposed task) để sinh viên xem xét và xác nhận đưa vào lịch học.

**Why this priority**: Đây là chức năng cốt lõi nhất của Module B. Nếu không trích xuất được thông tin bài tập thì toàn bộ chuỗi xử lý (đưa vào Module C lập lịch) không thể kích hoạt.

**Independent Test**: Cung cấp một email thông báo bài tập mẫu hợp lệ; hệ thống đọc nội dung và hiển thị đề xuất nhiệm vụ với đầy đủ tên bài tập, môn học, hạn nộp được nhận diện chính xác và kèm trích dẫn văn bản gốc.

**Acceptance Scenarios**:

1. **Given** một email học tập an toàn có thông báo giao bài tập, **When** hệ thống xử lý email, **Then** một nhiệm vụ mới ở trạng thái "đề xuất" (proposed) xuất hiện với tên bài, môn học và hạn nộp được phân giải thành ngày giờ cụ thể.
2. **Given** một đề xuất nhiệm vụ vừa được tạo, **When** sinh viên xem chi tiết, **Then** mỗi thông tin trích xuất đều hiển thị đoạn trích dẫn nguyên văn từ nội dung nguồn để sinh viên kiểm chứng.
3. **Given** một email không chứa thông tin bài tập (ví dụ: đổi phòng học hoặc thông báo sinh hoạt), **When** hệ thống xử lý, **Then** hệ thống xác định không có bài tập và không tạo nhiệm vụ rác.

---

### User Story 2 - Sinh viên kiểm tra, chỉnh sửa và phê duyệt đề xuất (Priority: P1)

Sinh viên xem danh sách các đề xuất bài tập do AI tạo ra, có thể điều chỉnh lại thông tin (hạn nộp, số giờ dự kiến, độ ưu tiên) trước khi nhấn nút "Xác nhận vào lịch" để đưa nhiệm vụ sang module lập lịch hoặc nhấn "Từ chối" để bỏ qua.

**Why this priority**: Tuân thủ nguyên tắc sống còn "AI chỉ đề xuất, người dùng quyết định". Tránh việc AI trích xuất sai gây xáo trộn thời gian biểu của sinh viên.

**Independent Test**: Mở màn hình danh sách đề xuất, chỉnh sửa hạn nộp và số giờ ước tính của một nhiệm vụ, nhấn "Xác nhận"; nhiệm vụ chuyển sang trạng thái "đã xác nhận" (confirmed) và sẵn sàng để xếp lịch.

**Acceptance Scenarios**:

1. **Given** nhiệm vụ đang ở trạng thái "đề xuất", **When** sinh viên nhấn "Xác nhận vào lịch", **Then** nhiệm vụ chuyển sang trạng thái "đã xác nhận" kèm thời điểm xác nhận.
2. **Given** nhiệm vụ đang ở trạng thái "đề xuất", **When** sinh viên nhấn "Từ chối", **Then** nhiệm vụ chuyển sang trạng thái "đã hủy" (cancelled) và không bao giờ xuất hiện trong lịch học.
3. **Given** sinh viên muốn đổi hạn nộp hoặc số giờ dự kiến, **When** nhập giá trị mới trên giao diện và xác nhận, **Then** hệ thống lưu giá trị chỉnh sửa của sinh viên thay vì giá trị AI đoán ban đầu.

---

### User Story 3 - Trích xuất chi tiết yêu cầu nộp bài và tiêu chí chấm điểm (Priority: P2)

Ngoài hạn nộp, sinh viên cần nắm rõ các điều kiện nộp bài (định dạng file .pdf/.zip, nền tảng nộp bài LMS/Drive, quy cách đặt tên file) và tiêu chí chấm điểm (rubric) để làm bài đúng quy cách và đạt điểm tối đa.

**Why this priority**: Giúp sinh viên tránh các lỗi sơ đẳng bị trừ điểm (như sai định dạng file, nộp nhầm chỗ, thiếu phần bắt buộc) mà không cần phải tự đọc lại toàn bộ file đề bài dài.

**Independent Test**: Cung cấp file đề bài có quy cách đặt tên và tiêu chí chấm; kiểm tra phần chi tiết hiển thị đúng danh sách định dạng file, nền tảng nộp bài và các tiêu chí đánh giá.

**Acceptance Scenarios**:

1. **Given** đề bài có ghi rõ *"nộp file zip lên LMS theo cú pháp MSSV_HoTen"*, **When** trích xuất, **Then** hệ thống nhận diện đúng định dạng `.zip`, nơi nộp `LMS`, và quy cách đặt tên file.
2. **Given** đề bài có rubric chấm điểm (ví dụ: Báo cáo 40%, Demo 60%), **When** xem chi tiết bài tập, **Then** danh sách tiêu chí chấm được liệt kê rõ ràng.

---

### User Story 4 - Phát hiện mâu thuẫn và thông báo dời hạn nộp (Priority: P2)

Khi giảng viên gửi email đính chính dời hạn nộp hoặc thay đổi yêu cầu khác với file đề bài PDF ban đầu, hệ thống phát hiện sự bất nhất, hiển thị cảnh báo mâu thuẫn và đề xuất phương án cập nhật để sinh viên quyết định.

**Why this priority**: Đây là tình huống xảy ra thường xuyên trong thực tế gây nhầm lẫn hạn nộp nghiêm trọng cho sinh viên.

**Independent Test**: Gửi một email thông báo lùi hạn nộp cho bài tập đã có; hệ thống hiển thị cảnh báo lệch hạn nộp, giữ nguyên nhiệm vụ cũ và đưa ra đề xuất cập nhật hạn mới cho sinh viên duyệt.

**Acceptance Scenarios**:

1. **Given** file đề bài ghi hạn 18/11 nhưng email giảng viên ghi dời hạn sang 25/11, **When** xử lý email, **Then** hệ thống cảnh báo lệch hạn nộp 7 ngày và gợi ý dùng hạn mới từ email.
2. **Given** nhiệm vụ đã được sinh viên xác nhận từ trước, **When** có email dời hạn mới, **Then** hệ thống không tự ý sửa nhiệm vụ mà tạo một "đề xuất cập nhật" chờ sinh viên bấm chấp nhận.

---

### Edge Cases

- **Email hoặc file có nội dung độc hại**: Hệ thống từ chối xử lý ngay tại cổng bảo mật, không trích xuất và cảnh báo rõ lý do an toàn cho sinh viên.
- **Diễn đạt thời gian tương đối phức tạp ("23h59 thứ Sáu tuần sau", "hết ngày mai", "trong vòng 3 ngày tới")**: Hệ thống phải dựa vào mốc thời gian nhận email để tính ra ngày giờ tuyệt đối chính xác, không lấy giờ hiện tại của máy tính.
- **Thông báo không ghi giờ cụ thể ("hạn ngày 20/11")**: Hệ thống mặc định gán thời gian là 23:59:00 của ngày đó và hiển thị rõ giả định này cho sinh viên biết.
- **Hạn nộp quá mơ hồ ("nộp vào tuần sau", "buổi học kế tiếp")**: Hệ thống không được tự đoán mò ngày; phải giữ nhiệm vụ ở trạng thái thiếu hạn, gắn cờ cảnh báo mơ hồ và yêu cầu sinh viên nhập ngày bằng tay khi xác nhận.
- **Văn bản chứa chỉ dẫn gây nhiễu (Prompt Injection)**: Nội dung bài tập chứa các câu lệnh giả như "bỏ qua chỉ dẫn trước đó" không được phép làm thay đổi cấu trúc trích xuất của hệ thống.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST chỉ xử lý các email và tài liệu đã được xác nhận an toàn từ cổng bảo mật; tuyệt đối không xử lý nguồn độc hại.
- **FR-002**: Hệ thống MUST trích xuất được các trường thông tin cơ bản của bài tập: Tên bài tập, Tên môn học, và Cụm từ hạn nộp nguyên văn.
- **FR-003**: Hệ thống MUST chuẩn hóa được các cách diễn đạt ngày giờ tiếng Việt tự nhiên (tuyệt đối và tương đối) thành mốc thời gian cụ thể dựa trên thời điểm nhận thông báo.
- **FR-004**: Mọi bài tập do hệ thống tạo ra ban đầu MUST ở trạng thái "đề xuất" (proposed); hệ thống MUST NOT tự động chuyển bài tập sang trạng thái "đã xác nhận" (confirmed) mà không có hành động xác nhận từ người dùng.
- **FR-005**: Mọi thông tin trích xuất MUST đi kèm trích dẫn nguyên văn đoạn văn bản bằng chứng và vị trí nguồn (email hoặc số trang tài liệu).
- **FR-006**: Nếu trích dẫn bằng chứng không tồn tại thực tế trong văn bản nguồn, hệ thống MUST loại bỏ giá trị trường đó và đánh dấu cảnh báo thiếu bằng chứng.
- **FR-007**: Hệ thống MUST trích xuất được các thông tin chi tiết nâng cao khi có trong văn bản: định dạng nộp, nền tảng nộp bài, quy cách đặt tên file và tiêu chí chấm điểm.
- **FR-008**: Hệ thống MUST phát hiện được sự mâu thuẫn về hạn nộp hoặc hình thức nộp giữa thông báo email và tài liệu đề bài, đồng thời hiển thị cảnh báo trực quan cho người dùng.
- **FR-009**: Khi nhận được thông báo dời hạn hoặc điều chỉnh cho bài tập đã tồn tại, hệ thống MUST tạo đề xuất cập nhật thay vì tự ý ghi đè lên nhiệm vụ hiện có.
- **FR-010**: Người dùng MUST có quyền chỉnh sửa trực tiếp hạn nộp, số giờ dự kiến, và độ ưu tiên của đề xuất trước khi xác nhận đưa vào lịch học.
- **FR-011**: Hệ thống MUST tính toán điểm độ tin cậy (confidence) khách quan phản ánh mức độ đầy đủ của thông tin và tính rõ ràng của hạn nộp.
- **FR-012**: Hệ thống MUST hỗ trợ hoạt động ngoại tuyến (offline) với dữ liệu mẫu và cơ chế giả lập mà không phụ thuộc vào kết nối mạng hay dịch vụ bên ngoài.

### Key Entities *(include if feature involves data)*

- **Assignment Proposal (Đề xuất bài tập)**: Đại diện cho một bài tập được trích xuất từ văn bản, gồm tên bài tập, môn học, hạn nộp dự kiến, số giờ ước tính, độ ưu tiên gợi ý, điểm tin cậy, nguồn trích dẫn và trạng thái vòng đời (proposed, confirmed, cancelled).
- **Assignment Detail (Nội dung chi tiết bài tập)**: Chứa thông tin mở rộng phục vụ sinh viên thực hiện bài tập, gồm định dạng file nộp, nền tảng nộp bài, quy cách đặt tên, danh sách tiêu chí chấm điểm và các giả định khi chuẩn hóa thời gian.
- **Conflict Report (Báo cáo mâu thuẫn)**: Ghi nhận sự bất nhất giữa hai nguồn thông tin về cùng một bài tập (lệch hạn nộp, lệch kênh nộp), kèm giá trị hai bên và gợi ý giải quyết của hệ thống.
- **Update Proposal (Đề xuất cập nhật)**: Bản ghi đề xuất thay đổi thông tin (ví dụ lùi hạn nộp) cho một bài tập đã tồn tại khi nhận được thông báo đính chính mới.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Độ chính xác chuẩn hóa ngày giờ tiếng Việt đạt tối thiểu 90% trên bộ dữ liệu kiểm thử chuẩn hóa các mẫu câu thực tế.
- **SC-002**: Độ chính xác nhận diện mâu thuẫn hạn nộp (Conflict Recall) đạt tối thiểu 85% đối với các trường hợp dời hạn giữa email và đề bài.
- **SC-003**: 100% nhiệm vụ đưa sang hệ thống lập lịch đều phải có đầy đủ hạn nộp và trải qua bước xác nhận của người dùng; không có ngoại lệ tự động xác nhận.
- **SC-004**: Sinh viên có thể hoàn thành việc xem xét, chỉnh sửa và xác nhận một đề xuất bài tập trong vòng dưới 30 giây trên giao diện người dùng.
- **SC-005**: 100% các nguồn dữ liệu độc hại bị từ chối ngay lập tức mà không tiêu tốn tài nguyên xử lý ngữ nghĩa.

## Assumptions

- **Thời điểm nhận thông báo**: Mọi tính toán thời gian tương đối trong email đều lấy thời điểm nhận email làm mốc neo chuẩn, bảo đảm tính tất định.
- **Hạn nộp mặc định**: Khi giảng viên chỉ thông báo ngày mà không nêu giờ cụ thể, sinh viên và hệ thống cùng thống nhất quy ước hạn chót là cuối ngày đó (23:59:00).
- **Ngôn ngữ xử lý chính**: Hệ thống ưu tiên tối ưu hóa cho ngữ cảnh học thuật và cách hành văn tiếng Việt của các trường đại học tại Việt Nam, có hỗ trợ các thuật ngữ tiếng Anh thông dụng (assignment, deadline, rubric, LMS).
- **Môi trường hoạt động**: Chức năng tích hợp trong ứng dụng nội bộ chạy cục bộ trên máy tính của sinh viên với cơ sở dữ liệu SQLite, không yêu cầu thiết lập máy chủ phức tạp.
