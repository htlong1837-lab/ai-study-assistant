# SP1 — Báo cáo phân tích sự cần thiết của hệ thống: Trợ lý AI học tập và lịch trình

*Bản nháp do Claude soạn ngày 22/11/2026 từ tài liệu trong repo và nguồn công khai, Long và nhóm đọc
lại, sửa bằng lời của mình trước khi nộp. Các chỗ **[Cần số liệu khảo sát]** phải điền bằng kết quả
khảo sát thật của nhóm (bộ câu hỏi: `docs/khao-sat/cau-hoi-google-form.md`); không tự điền số.
Nếu nhóm đã nộp SP1 từ trước thì dùng bản đã nộp, file này chỉ để đối chiếu.*

## 1. Bối cảnh và vấn đề thực tiễn

Một sinh viên đại học học cùng lúc 6–8 học phần. Thông tin về bài tập đến từ nhiều kênh khác nhau:
hệ thống quản lý học tập (LMS) của trường, email giảng viên, file đề bài PDF, slide bài giảng, nhóm
chat lớp. Hạn nộp được viết bằng tiếng Việt tự nhiên ("23h59 thứ Sáu tuần sau", "trước buổi học
tới"), có khi bị dời qua một email khác mà LMS chưa cập nhật.

Hệ quả là sinh viên phải tự gom thông tin, tự nhớ hạn và tự sắp thời gian học. Đây là bối cảnh thuận
lợi cho việc trì hoãn: tổng hợp của Steel (2007) trích các khảo sát cho thấy khoảng 75% sinh viên tự
nhận mình hay trì hoãn và gần một nửa trì hoãn thường xuyên, thành vấn đề. Cùng lúc, email là một kênh
tấn công phổ biến: email giả mạo trường học, link rút gọn, tệp đính kèm độc.

**Vấn đề hệ thống giải quyết:** biến các thông báo phân tán (email, đề bài) thành danh sách nhiệm vụ có
hạn nộp đã được kiểm chứng, xếp thành lịch tự học khả thi quanh thời khoá biểu, đồng thời chặn nội dung
độc trước khi xử lý.

**[Cần số liệu khảo sát]:** tỉ lệ sinh viên từng quên hoặc nhầm hạn nộp trong học kỳ; số kênh nhận
thông báo bài tập trung bình; tỉ lệ từng nhận email giả mạo/đáng ngờ.

## 2. Đối tượng người dùng và nhu cầu

**Người dùng chính:** sinh viên đại học, ưu tiên sinh viên năm 1–3 học nhiều học phần cùng lúc, nhận
thông báo chủ yếu qua email và LMS.

| Nhu cầu | Biểu hiện | Chức năng đáp ứng |
|---|---|---|
| Không bỏ sót bài tập | Bài tập nằm rải rác trong email, PDF | B: trích nhiệm vụ từ email và đề bài |
| Biết đúng hạn nộp | Hạn viết tự nhiên, bị dời, email và đề bài lệch nhau | B: chuẩn hoá ngày giờ tiếng Việt, cảnh báo mâu thuẫn |
| Có thời gian làm kịp | Dồn việc sát hạn | C: xếp khối tự học quanh thời khoá biểu, nhắc nhở |
| Hiểu nhanh tài liệu dài | Đề bài, giáo trình nhiều trang | A: hỏi đáp có trích dẫn trang |
| An toàn khi mở email | Email giả mạo, tệp độc | D: phân loại, quét link và tệp, chặn trước khi xử lý |
| Kiểm soát được AI | Sợ AI tự ý thêm/sửa lịch | Mọi kết quả AI là "đề xuất", người dùng xác nhận |

**[Cần số liệu khảo sát]:** mức độ quan tâm tới từng chức năng (thang 1–5), mức độ yên tâm khi để AI đọc
email, công cụ đang dùng để nhớ hạn.

## 3. Khảo sát các giải pháp hiện có

*Tra cứu trang chính thức và tài liệu hướng dẫn; tính năng có thể đã đổi, cần mở lại liên kết trước khi
nộp. Chi tiết hơn: mục B.6 (`B-trich-xuat.md`) và C.6 (`C-lap-lich.md`).*

| Giải pháp | Làm được | Chưa làm được (so với nhu cầu ở mục 2) |
|---|---|---|
| **LMS của trường (Moodle)** | Hạn nộp của hoạt động bài tập tự hiện trên lịch; khối "Upcoming events"; có thể gửi email nhắc trước hạn 7, 3, 1 ngày nếu trường bật | Chỉ biết bài tập giảng viên tạo trên LMS; không đọc email/PDF; không xếp lịch học; nhắc nhở tuỳ cấu hình từng trường |
| **Todoist** | Nhập việc bằng ngôn ngữ tự nhiên; Todoist Assist có "Email Assist" (gói Pro/Business) biến email chuyển tiếp thành việc, lấy cả hạn nộp | Không đọc đề bài PDF; không phát hiện mâu thuẫn giữa nguồn; không quét an toàn email; không xếp khối học quanh thời khoá biểu; tính năng email cần trả phí |
| **Google Calendar** | Tạo việc trên lịch, khối Focus time | Người dùng tự đặt giờ, không tự xếp việc theo hạn nộp |
| **Motion** | Tự xếp và tự xếp lại việc vào giờ rảnh theo hạn, ưu tiên | Người dùng tự nhập việc; trả phí (từ 19 USD/tháng); không công bố thuật toán; không hướng tới sinh viên |
| **Chatbot tổng quát (ChatGPT, Gemini)** | Tóm tắt email, trả lời câu hỏi về tài liệu | Không gắn với lịch; có thể bịa trích dẫn; người dùng phải tự dán nội dung; không có bước chặn nội dung độc |

**Nhận xét:** từng mảnh (nhắc hạn, nhập việc bằng ngôn ngữ tự nhiên, tự xếp lịch, hỏi đáp tài liệu) đã
có ở các sản phẩm khác. Chưa có giải pháp nào nối liền **email → kiểm tra an toàn → trích hạn nộp →
người dùng xác nhận → lịch tự học** cho sinh viên, miễn phí, và đo được chất lượng từng bước.

## 4. Lý do cần xây dựng hệ thống

1. **Thông tin bài tập phân tán, không công cụ nào gom từ email và đề bài:** LMS chỉ thấy bài tập trên
   LMS, Todoist/Motion cần người dùng tự nhập (hoặc trả phí).
2. **Hạn nộp tiếng Việt tự nhiên và hay thay đổi:** cần chuẩn hoá và phát hiện mâu thuẫn, điều các
   công cụ hiện có không làm.
3. **Biết hạn chưa đủ, cần thời gian làm:** cần xếp khối tự học khả thi quanh thời khoá biểu, có giới hạn
   giờ mỗi ngày.
4. **Đưa email vào AI phải an toàn:** cần chặn email/tệp độc và che thông tin cá nhân trước khi gửi LLM.

## 5. Vai trò và lợi ích của việc tích hợp AI

| Chức năng | Vai trò của AI | Vì sao cần AI (không làm bằng luật đơn thuần) |
|---|---|---|
| Phân loại email, phát hiện lừa đảo (D) | TF-IDF + hồi quy logistic; LLM zero-shot để so sánh | Nội dung email đa dạng, luật từ khoá dễ bị qua mặt |
| Trích xuất bài tập (B) | LLM trích có cấu trúc, bắt buộc kèm câu trích trong nguồn | Cách giảng viên viết thông báo rất khác nhau |
| Hỏi đáp tài liệu (A) | LLM trả lời kèm trích dẫn trang, kiểm chứng trích dẫn | Hiểu câu hỏi tự nhiên trên tài liệu dài |
| Xếp lịch (C) | Tối ưu ràng buộc (CP-SAT), so với EDF | Nhiều ràng buộc cùng lúc, cần tối ưu chứ không chỉ "hạn gần làm trước" |

**Lợi ích:** giảm thời gian tự gom và nhập việc; ít bỏ sót, nhầm hạn; lịch học đều hơn (thí nghiệm C:
đỉnh tải giảm từ 4 xuống 1–2,15 giờ/ngày ở kịch bản nhẹ/vừa); an toàn hơn khi mở email.

**Giữ con người trong vòng quyết định:** AI chỉ đề xuất; người dùng duyệt email nghi ngờ, xác nhận
nhiệm vụ, chọn việc cần xếp. Mọi trích xuất phải kèm câu trích có thật trong nguồn để kiểm tra lại.

## 6. Mục tiêu, phạm vi và kết quả kỳ vọng

**Mục tiêu:** một ứng dụng chạy được trên máy cá nhân, nhận email `.eml` và tài liệu, trả về danh sách
nhiệm vụ đã kiểm chứng và lịch tự học có nhắc nhở.

**Trong phạm vi (5 tuần):** nhập file `.eml`; phân loại và quét an toàn; trích nhiệm vụ từ email và PDF;
hỏi đáp tài liệu có trích dẫn; xếp lịch EDF/CP-SAT; nhắc qua Telegram và file `.ics`; giao diện
Streamlit.

**Ngoài phạm vi:** kết nối trực tiếp Gmail/Outlook; đồng bộ hai chiều Google Calendar; OCR PDF scan;
ứng dụng di động; tự huấn luyện mô hình ngôn ngữ.

**Kết quả kỳ vọng và cách đo**

| Chức năng | Chỉ số | Phương pháp cơ sở để so sánh |
|---|---|---|
| D — phân loại email | Macro-F1; Precision/Recall phát hiện lừa đảo | TF-IDF so với LLM zero-shot |
| B — trích xuất | F1 theo trường; độ chính xác hạn nộp | Regex/heuristic |
| A — hỏi đáp | Tỉ lệ đúng trang, tỉ lệ trích dẫn có thật, tỉ lệ từ chối đúng câu không có đáp án | Chatbot không có tài liệu |
| C — lập lịch | Giờ thiếu có trọng số, đỉnh tải, số khối, thời gian chạy | EDF |

## Tài liệu tham khảo

- Steel, P. (2007). The nature of procrastination: A meta-analytic and theoretical review of quintessential
  self-regulatory failure. *Psychological Bulletin*, 133(1), 65–94.
  https://prism.ucalgary.ca/handle/1880/47914
- Moodle Docs — Calendar. https://docs.moodle.org/test/Calendar
- University of Warwick — Moodle reminders. https://warwick.ac.uk/services/digitallearning/support/guides/moodle-guides/reminders/
- Todoist Help — Introduction to Todoist Assist. https://www.todoist.com/help/articles/introduction-to-todoist-assist-KgPP22q5O
- Google Calendar, Motion: xem nguồn trong mục C.6 của `C-lap-lich.md`.
