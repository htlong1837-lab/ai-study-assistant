# SP2 — Báo cáo sản phẩm: Trợ lý AI học tập và lịch trình

*Khung báo cáo theo đề bài (Application Track, Sản phẩm 2). Long ghép bản cuối. Mỗi người viết phần
module của mình trong file riêng `docs/report/<A|B|C|D>-*.md`, theo cùng cấu trúc với
[C-lap-lich.md](C-lap-lich.md): bài toán → phương pháp và lý do chọn → tích hợp → thí nghiệm →
hạn chế → khảo sát.*

**Hạn chốt:** nháp từng phần cuối tuần 4; bản ghép tuần 5 (theo kế hoạch nhóm).

| Mục theo đề bài | Nội dung | Phụ trách | Trạng thái |
|---|---|---|---|
| 1. Tổng quan hệ thống và các chức năng | Luồng email → lịch, 4 module | Long | Khung sẵn (dưới) |
| 2. Kiến trúc và thiết kế hệ thống | Sơ đồ, hợp đồng dữ liệu, nguyên tắc | Long | Khung sẵn (dưới) |
| 3. Phương pháp, mô hình hoặc công nghệ AI | Từng module | Cả nhóm | B, C: xong nháp; A, D: chưa |
| 4. Cách thức tích hợp AI vào hệ thống | Từng module + bước xác nhận | Cả nhóm | B, C: xong nháp |
| 5. Quy trình triển khai và kết quả đạt được | spec-kit, Git, lộ trình 5 tuần | Long | Chưa |
| 6. Kiểm thử, đánh giá và phân tích kết quả | Từng module + kiểm thử tự động | Cả nhóm | C: xong nháp |
| 7. Hạn chế và hướng phát triển | Gộp từ các module | Long | Chưa |
| Phụ lục: cài đặt, sử dụng, demo | README, kịch bản demo | Hoàng Minh | Chưa |

---

## 1. Tổng quan hệ thống

Sinh viên nhận bài tập qua nhiều kênh (email giảng viên, file đề bài, giáo trình), phải tự theo dõi
hạn nộp và tự sắp thời gian học. Hệ thống gom các nguồn này thành một luồng:

1. **D — Email & bảo mật:** nhập email, phân loại, kiểm tra link và file đính kèm; chặn nội dung độc.
2. **A — Hỏi đáp tài liệu:** đọc PDF theo trang, trả lời câu hỏi kèm trích dẫn trang.
3. **B — Trích xuất bài tập:** từ email và đề bài, trích tên việc, hạn nộp, yêu cầu → đề xuất
   nhiệm vụ.
4. **Người dùng xác nhận** từng đề xuất.
5. **C — Lập lịch & nhắc nhở:** xếp khối tự học quanh thời khoá biểu, nhắc qua Telegram hoặc `.ics`.

*[Mỗi module bổ sung 2–3 câu mô tả chức năng người dùng thấy được, kèm ảnh chụp màn hình.]*

## 2. Kiến trúc và thiết kế

### 2.1. Kiến trúc tổng thể

Một ứng dụng Streamlit duy nhất (`app.py`), mỗi module một trang (`views/`), logic trong
`modules/<module>/` không phụ thuộc giao diện để kiểm thử được. Dữ liệu cục bộ (SQLite, file).
Mọi lời gọi LLM đi qua một cửa chung `core/llm_client.py` (cache, đếm token, chạy được khi thiếu
khóa).

*[Chèn sơ đồ luồng — có sẵn trên trang chủ ứng dụng; chụp lại hoặc vẽ bằng draw.io.]*

### 2.2. Hợp đồng dữ liệu giữa các module

Các module chỉ trao đổi qua dataclass trong `core/contracts.py`, mỗi loại có dữ liệu giả
(`core/mocks.py`) để 4 người làm song song.

| Từ → Đến | Dữ liệu | Trường chính |
|---|---|---|
| D → B | `ClassifiedEmail` | id, người gửi, tiêu đề, nội dung, nhãn, tóm tắt, tệp đính kèm, trạng thái an toàn |
| D → A | `SafeAttachment` | đường dẫn, SHA-256, email gốc |
| A → B | `ParsedDocument` | mã tài liệu, danh sách trang (số trang, văn bản) |
| B → C | `Task` | tên, môn, hạn nộp, số giờ, ưu tiên, nguồn, độ tin cậy, trạng thái |
| C → người dùng | `StudyBlock`, `Reminder` | nhiệm vụ, giờ bắt đầu/kết thúc; thời điểm, kênh, nội dung |

### 2.3. Nguyên tắc thiết kế (constitution của dự án)

1. **AI chỉ đề xuất, người dùng quyết định.** Mọi kết quả AI mang trạng thái "đề xuất" kèm nguồn;
   chỉ nhiệm vụ đã xác nhận mới vào lịch.
2. **Chặn tại cổng.** Nội dung "độc" không bao giờ đến A hoặc B.
3. **Hợp đồng chung, module độc lập.**
4. **Đo được:** mỗi chức năng AI có chỉ số và phương pháp cơ sở để so sánh.
5. **Chạy được trên máy lạ, không cần khóa API** cho luồng lập lịch.

## 3–4. Phương pháp AI và cách tích hợp

| Module | Phương pháp | So sánh với | Chi tiết |
|---|---|---|---|
| A | LLM đọc PDF qua API, trả lời kèm trích dẫn trang | Chatbot không có tài liệu; tự dựng RAG | *[A-hoi-dap.md]* |
| B | LLM trích xuất có cấu trúc + luật chuẩn hoá ngày giờ tiếng Việt | Heuristic Regex; PhoBERT-NER | [B-trich-xuat.md](B-trich-xuat.md) |
| C | Thoả mãn ràng buộc có tối ưu (CP-SAT) | EDF tham lam | [C-lap-lich.md](C-lap-lich.md) |
| D | TF-IDF + hồi quy logistic; LLM zero-shot; heuristic URL + VirusTotal | So sánh lẫn nhau | *[D-email-bao-mat.md]* |

## 5. Quy trình triển khai

*[Long viết: spec-kit (constitution → specify → plan → tasks → implement, thư mục `specs/`), Git
với nhánh và pull request, lộ trình 5 tuần và mốc nối luồng cuối tuần 3, những gì đạt/chưa đạt.]*

## 6. Kiểm thử và đánh giá

- **Kiểm thử tự động:** `pytest`, chạy không cần mạng. *[Cập nhật số test cuối cùng.]*
- **Đánh giá từng module:** bảng chỉ số trong file của từng module.
- **Kiểm thử luồng đầu–cuối:** *[một email mẫu đi hết luồng — làm sau mốc tuần 3.]*

## 7. Hạn chế và hướng phát triển

*[Gộp mục hạn chế của 4 module; cộng các phần đã cắt khỏi phạm vi: tự dựng RAG, fine-tune PhoBERT,
lệnh bằng giọng nói, đồng bộ Google Calendar, Docker/CI, Gmail API.]*
