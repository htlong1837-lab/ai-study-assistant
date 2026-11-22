# SP2 — Báo cáo sản phẩm: Trợ lý AI học tập và lịch trình

*Khung báo cáo theo đề bài (Application Track, Sản phẩm 2). Long ghép bản cuối. Mỗi người viết phần
module của mình trong file riêng `docs/report/<A|B|C|D>-*.md`, theo cùng cấu trúc với
[C-lap-lich.md](C-lap-lich.md): bài toán → phương pháp và lý do chọn → tích hợp → thí nghiệm →
hạn chế → khảo sát.*

**Hạn chốt:** nháp từng phần cuối tuần 4; bản ghép tuần 5 (theo kế hoạch nhóm).

| Mục theo đề bài | Nội dung | Phụ trách | Trạng thái (22/11) |
|---|---|---|---|
| 1. Tổng quan hệ thống và các chức năng | Luồng email → lịch, 4 module | Long | Có nháp; thiếu ảnh chụp màn hình |
| 2. Kiến trúc và thiết kế hệ thống | Sơ đồ, hợp đồng dữ liệu, nguyên tắc | Long | Có nháp; thiếu sơ đồ |
| 3. Phương pháp, mô hình hoặc công nghệ AI | Từng module | Cả nhóm | A, B, C, D: có báo cáo riêng |
| 4. Cách thức tích hợp AI vào hệ thống | Từng module + bước xác nhận | Cả nhóm | Có nháp (mục 3–4 bên dưới) |
| 5. Quy trình triển khai và kết quả đạt được | spec-kit, Git, lộ trình 5 tuần | Long | Có nháp (Claude soạn, Long cần đọc lại) |
| 6. Kiểm thử, đánh giá và phân tích kết quả | Từng module + kiểm thử tự động | Cả nhóm | Có nháp; B chưa có số đo |
| 7. Hạn chế và hướng phát triển | Gộp từ các module | Long | Có nháp |
| Phụ lục: cài đặt, sử dụng, demo | README, kịch bản demo | Hoàng Minh | README có; kịch bản demo: `docs/demo-kich-ban.md` |

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
| A | LLM đọc PDF qua API, trả lời kèm trích dẫn trang, kiểm chứng trích dẫn | Chatbot không có tài liệu; tự dựng RAG | [A-hoi-dap.md](A-hoi-dap.md) |
| B | LLM trích xuất có cấu trúc + luật chuẩn hoá ngày giờ tiếng Việt | Heuristic Regex; PhoBERT-NER | [B-trich-xuat.md](B-trich-xuat.md) |
| C | Thoả mãn ràng buộc có tối ưu (CP-SAT) | EDF tham lam | [C-lap-lich.md](C-lap-lich.md) |
| D | TF-IDF + hồi quy logistic; LLM zero-shot; heuristic URL + VirusTotal | So sánh lẫn nhau | [D-email-bao-mat.md](D-email-bao-mat.md) |

**Tích hợp giữa các module (đã nối, 20–22/11):**

- **D → B:** người dùng duyệt email ở trang Email & bảo mật → `publish_to_modules` ghi email vào phiên
  làm việc → trang Trích xuất đọc qua `modules/extraction/intake.py`. Email nghi ngờ chỉ đi tiếp khi
  người dùng đã duyệt (`allow_suspicious=True`); email độc bị chặn ở cả D (`publish_to_modules`) và B
  (`ensure_safe`).
- **D → A:** tệp đính kèm an toàn đi cùng đường đó; trang Hỏi đáp đọc lại tệp và kiểm tra SHA-256 khớp
  giá trị D ghi lúc quét rồi mới mở. Trang Hỏi đáp không cho tải tài liệu thẳng.
- **B → C:** nhiệm vụ B lưu trong SQLite được đổi sang `contracts.Task` (`modules/scheduler/source.py`);
  chỉ nhiệm vụ đã xác nhận được xếp lịch.
- **AI chỉ đề xuất:** ba điểm người dùng quyết định — duyệt email nghi ngờ (D), xác nhận nhiệm vụ (B),
  tích nhiệm vụ cần xếp (C).

## 5. Quy trình triển khai

*[Nháp do Claude soạn từ lịch sử repo; Long đọc lại, sửa bằng lời mình.]*

**Đặc tả trước, code sau (spec-kit).** Bắt đầu bằng bộ nguyên tắc dự án (constitution, 5 nguyên tắc ở
mục 2.3), rồi mỗi phần có một thư mục đặc tả trong `specs/`: `001-project-skeleton`, `002-scheduler`,
`003-scheduler-experiments`, `004-assignment-extraction`, `005-document-qna`. Mỗi đặc tả đi theo các bước
specify → plan → tasks → implement. Module D lập kế hoạch theo gói việc WP-00…WP-08
(`docs/plan_module_d.md`).

**Làm song song nhờ hợp đồng dữ liệu.** Khung dự án (06/11) chốt trước các dataclass trong
`core/contracts.py` và dữ liệu giả `core/mocks.py`, nên 4 người làm module của mình mà không chờ nhau;
khi module trước xong chỉ cần thay dữ liệu giả bằng dữ liệu thật.

**Git và review.** Mỗi người làm trên nhánh riêng, mở pull request vào `main`; Long review và merge
(15 pull request mở từ 06/11 đến 22/11, 13 được merge). CI trên GitHub Actions chạy cho mọi thay đổi code: `ruff` (kiểm
tra code) và `pytest` toàn repo với ngưỡng độ phủ 80%. Có lỗi chỉ CI bắt được, ví dụ lọc tên tệp đính
kèm kiểu `..\..\evil.exe` chỉ sai trên Linux.

**Lộ trình 5 tuần và kết quả.**

| Tuần | Mục tiêu | Kết quả |
|---|---|---|
| 1 (đến 06/11) | Repo, hợp đồng dữ liệu, mẫu nhật ký AI | Đạt |
| 2 (đến 09/11) | Mỗi module chạy trên dữ liệu giả, có trang | C, A đạt; D có lõi đúng hạn nhưng trang còn tạm; B vào main trễ 2 ngày |
| 3 (đến 16/11) | Nối luồng email → lịch | Trễ: nối xong 20–22/11 |
| 4 | Số liệu đánh giá, cài được trên máy khác | A (Gemini thật), C (thí nghiệm) có số; B, D mới đo trên dữ liệu tự tạo |
| 5 | SP2, SP3, tổng duyệt demo | Đang làm |

**Kết quả đạt được:** ứng dụng 5 trang chạy được trên máy không có khóa API (LLM giả cho luồng chính),
luồng D → B → C và D → A đã nối, 656 kiểm thử tự động đều đạt, độ phủ 85%.

## 6. Kiểm thử và đánh giá

### 6.1. Kiểm thử tự động

`pytest`, chạy không cần mạng (LLM giả; mạng bị chặn trong test của D). Số liệu ngày 22/11:

| Phần | Số test | Nội dung chính |
|---|---:|---|
| D — Email & bảo mật | 330 | Đọc `.eml`, lọc tên tệp, cổng chặn, quét URL/tệp, VirusTotal (giả lập), chuyển giao sang A/B, trang |
| A — Hỏi đáp | 123 | Kiểm chứng trích dẫn, đọc JSON từ LLM, trình đọc PDF, khóa API |
| B — Trích xuất | 105 | Chuẩn hoá ngày giờ tiếng Việt, kiểm chứng câu trích, so khớp, mâu thuẫn, luồng xác nhận, nhận email từ D |
| C — Lập lịch | 45 | Ràng buộc, EDF, CP-SAT (không tệ hơn EDF), nhắc nhở, nhận task từ B |
| Khung + khác | 53 | Hợp đồng dữ liệu, mock, LLM client, 5 trang mở không lỗi, không lộ khóa |
| **Tổng** | **656** | Độ phủ 85% (`modules`, `core`, `db`); riêng A 88% |

### 6.2. Đánh giá chức năng AI

| Module | Dữ liệu | Kết quả chính | Mức tin cậy |
|---|---|---|---|
| A | 30 câu hỏi trên 1 giáo trình, **Gemini thật** (19/11) | Tìm đúng trang 91–96%; từ chối đúng 6/6 câu không có đáp án; 1/30 câu bị từ chối do trích dẫn không có trong tài liệu | Bộ câu hỏi chưa được người rà soát hết |
| B | 20 email tự soạn (`eval/gold`) | *[Chưa có số đo — Duy chạy `eval/run_eval.py` với Gemini thật]* | — |
| C | Dữ liệu tổng hợp, 3 kịch bản × 10 seed | Quá tải: CP-SAT giảm giờ thiếu có trọng số 24,1 → 16,5 và giờ thiếu việc ưu tiên cao 2,7 → 0,65; nhẹ/vừa: đỉnh tải 4 → 1–2,15 giờ/ngày | Dữ liệu tổng hợp |
| D | 60 email tự tạo | TF-IDF Macro-F1 0,50; quét URL và tệp: Precision/Recall 1,0 trên bộ ca tự tạo; phishing 0,25/0,30 | Dữ liệu tự tạo; F1 của LLM đo bằng LLM giả nên không dùng được |

**Phân tích.** Hai phần có số liệu đáng tin nhất là A (chạy với LLM thật) và C (thí nghiệm lặp 10 lần, có
phương pháp cơ sở). B và D mới có số trên dữ liệu nhóm tự tạo, nên chỉ chứng minh hệ thống chạy đúng
thiết kế, chưa nói được chất lượng trên email thật. Phishing của D thấp (recall 0,30) cho thấy phân loại
văn bản một mình không đủ; hệ thống dựa vào quét URL/tệp và bước người dùng duyệt để bù.

### 6.3. Kiểm thử luồng đầu–cuối

Có test tự động đi trọn đường: D `publish_to_modules` → B `process_email` (thiếu cờ duyệt thì B chặn, có cờ
thì cho qua); B lưu task → C chỉ xếp task đã xác nhận; D chuyển tệp → A kiểm tra SHA-256 (tệp bị sửa sau
khi quét thì bị từ chối). *[Chạy thử trên app theo `docs/demo-kich-ban.md` và ghi kết quả.]*

## 7. Hạn chế và hướng phát triển

**Hạn chế**
- **Thiếu đánh giá trên dữ liệu thật** ở B và D (mục 6.2). Email thật có thông tin cá nhân nên cần thu
  thập có đồng ý và ẩn danh.
- **Phụ thuộc LLM thương mại** (Gemini) cho A và B: cần khóa API, có độ trễ (A: p95 33–79 giây) và kết
  quả thay đổi theo phiên bản mô hình.
- **Phát hiện phishing yếu** khi chỉ dựa vào văn bản; VirusTotal cần khóa và có giới hạn lượt gọi.
- **Không có OCR:** PDF scan không đọc được.
- **Phiên làm việc không lưu:** email đã duyệt chỉ nằm trong phiên Streamlit; tải lại trang là phải
  duyệt lại (task của B thì đã lưu SQLite).
- **Chưa nối hộp thư thật:** chỉ nhận file `.eml` tải lên, chưa đọc Gmail/Outlook.
- **Lập lịch:** trọng số mục tiêu do nhóm tự đặt; chưa xếp lại khi sinh viên bỏ lỡ một khối.

**Hướng phát triển**
- Thu thập bộ email thật có đồng ý để đánh giá B và D; thử thêm bộ phishing công khai cho D.
- Kết nối Gmail API (đã cắt khỏi phạm vi 5 tuần), đồng bộ hai chiều với Google Calendar.
- Tự dựng RAG hoặc mô hình chạy cục bộ để giảm phụ thuộc API; fine-tune PhoBERT cho trích xuất.
- Lưu trạng thái duyệt email vào CSDL; xếp lại lịch theo tiến độ thật.
