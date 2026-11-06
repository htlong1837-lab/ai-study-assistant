# AI-002 — Chiến lược, khung dự án, module C, thí nghiệm, nháp báo cáo phần C

| Trường thông tin | Nội dung |
|---|---|
| Mã tương tác | AI-002 |
| Người thực hiện | Long |
| Thời gian | 2026-11-06 (một phiên dài, nhiều lượt) |
| Công cụ AI | Claude Code (Claude Opus 5.5), ứng dụng desktop, có quyền chạy lệnh và sửa file trong repo |
| Mục đích | Lập chiến lược; tạo repo; khung dự án; module C (EDF, CP-SAT, nhắc nhở); thí nghiệm; nháp SP2 phần C |
| Prompt đầy đủ | Mục "Hội thoại" bên dưới (nguyên văn) |
| Phản hồi đầy đủ | File xuất gốc: `session-export-1793952087648.zip` (lưu trong Downloads của Long, đính kèm khi nộp SP3). Bên dưới chỉ tóm tắt. |
| Nhận xét, đánh giá | *[Long tự viết]* |
| Nội dung được sử dụng | *[Long tự viết — gợi ý: những commit nào giữ nguyên]* |
| Nội dung chỉnh sửa hoặc loại bỏ | *[Long tự viết — gợi ý: bỏ Dify; các điểm ở mục "Các lần AI tự phát hiện sai" bên dưới]* |
| Cách kiểm chứng | *[Long tự viết — gợi ý: chạy pytest, mở app, đọc lại research.md, mở lại nguồn Motion/Google]* |
| Kết quả áp dụng | Repo `htlong1837-lab/ai-study-assistant`: PR #1 (khung), PR #2 (module C), commit `862aa24` (thí nghiệm) và commit tiếp theo (khảo sát, khung SP2) |

## Hội thoại (prompt nguyên văn, phản hồi tóm tắt)

| Lượt | Prompt của Long | Phản hồi của AI (tóm tắt) |
|---|---|---|
| 1 | "hiện tại t đang phải làm bài giữa kì nnay, đọc plan, đưa ra chiến lược giúp t hoàn thiện phần của Long + sườn dự án( phần chính là lịch trình), sử dụng repo speckit. và defy để làm. đưa plan thứ m định làm ra để t duyệt trc khi bắt tay vào việc" (kèm đề PDF và kế hoạch DOCX) | Đọc đề và kế hoạch; đề xuất 4 giai đoạn; hiểu "defy" là Dify |
| 2 | "giai đoạn 0: cái này nếu cài trên máy lạ cx phải tự làm à" | spec-kit không cần trên máy khác; Dify tự host thì máy nào cũng phải cài → đề xuất Dify Cloud + dự phòng |
| 3 | "có nên cho dify vào k" | Khuyên **không**: phần chính của C là CP-SAT không cần LLM; Dify đi ngược quyết định bỏ Docker, thêm phụ thuộc mạng |
| 4 | "ok bỏ, tọ luôn repo cho t đi, acc đã cấp sẵn r" | Tạo repo private bằng spec-kit, push commit đầu |
| 5 | "cho t cái đường dẫn để add vào github desktop nào" | Đường dẫn thư mục và URL clone |
| 6 | "Làm Giai đoạn 1" | Constitution v1.0.0, spec 001, hợp đồng dữ liệu, mock, LLM client, 5 trang, 40 test |
| 7 | "Push và mở PR" | PR #1 |
| 8 | "cái pull đấy accept như nào" | Hướng dẫn merge trên web |
| 9 | "ok bắt đầu xây dự án xem nào" | Spec 002; EDF, CP-SAT, nhắc nhở, lịch tuần; 75 test |
| 10 | "Push và mở PR" | PR #2 |
| 11 | "ok tiếp đã merge" | Spec 003; thí nghiệm 3 kịch bản × 10 seed; nháp báo cáo phần C |
| 12 | "pussh thawnrg leen main ddi" | Gộp fast-forward vào main, push (không qua PR) |
| 13 | "ok tieeps" | Khảo sát Google Calendar/Motion có nguồn; khung SP2; file nhật ký này |

## Các lần AI tự phát hiện sai và sửa trong phiên (dữ kiện để Long đánh giá)

1. **Lịch CP-SAT bị băm vụn.** Bản đầu tối ưu đúng mục tiêu (đỉnh tải 1 giờ/ngày) nhưng ra 37 khối,
   phần lớn 30 phút. Phát hiện khi mở app xem lịch → thêm ràng buộc khối tối thiểu 60 phút.
2. **CP-SAT luôn chạy hết 10 giây.** Đo khoảng cách tới cận dưới, thấy chỉ chênh ở số khối → thêm
   điều kiện dừng `absolute_gap_limit`.
3. **CP-SAT thua EDF ở kịch bản quá tải** khi giới hạn 5 giây (35,5 so với 20 giờ thiếu), kết quả
   dao động giữa các lần chạy. Thử 20–60 giây thấy do hết giờ → thêm khởi động ấm bằng lời giải EDF.
   Thí nghiệm chính thức vẫn còn 1/10 seed CP-SAT thua (đã ghi trong báo cáo).
4. **Spec 003 hứa kết quả tái lập "giống hệt"** — sai với các ca CP-SAT hết giờ; đã sửa spec.
5. **Câu về định lý Jackson** viết quá mạnh ("EDF tối ưu") → sửa thành "tối thiểu hoá độ trễ lớn
   nhất trong trường hợp đơn giản"; vẫn cần Long kiểm chứng bằng tài liệu gốc.
6. **Bảng khảo sát** có ô "Google Calendar có giao diện tiếng Việt" viết theo trí nhớ, không có
   nguồn → đã thay.
7. **Lỗi khi phát triển:** sau khi sửa code, kết quả cũ trong Streamlit dùng lớp `TaskStatus` cũ nên
   trang báo "chưa có nhiệm vụ nào được xác nhận" → thêm kiểm tra bỏ kết quả cũ.

## Phần còn phải kiểm chứng (đã đánh dấu trong `docs/report/C-lap-lich.md`)

- Nguồn gốc quy tắc EDD (Jackson 1955).
- Nhận định "PuLP/CBC chậm hơn CP-SAT" — chưa đo trong đồ án.
- Thông tin Motion/Google Calendar (tra ngày 06/11/2026; trang giá Motion ghi "This plan is not available").
- Gửi Telegram với bot thật; nhập `.ics` vào Google Calendar.
