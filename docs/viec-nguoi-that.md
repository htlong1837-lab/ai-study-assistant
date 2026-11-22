# Việc chỉ người thật làm được (cập nhật 22/11)

*Claude đã làm xong phần làm được bằng code và tài liệu: merge PR #14, #15, gộp hai cách nối D → A,
đóng PR #10, nháp SP1, nháp SP2 mục 4–7, kịch bản demo, bộ email demo, bộ câu hỏi khảo sát.
Những việc dưới đây Claude **không làm thay** vì đề bài cấm nhật ký giả ("Không được tạo nhật ký giả
hoặc làm sai lệch lịch sử sử dụng AI") và vì số liệu khảo sát, dữ liệu thật phải đến từ người thật.
Mỗi mục đã có sẵn tư liệu để làm nhanh.*

## Cả nhóm

1. **Khảo sát SP1:** dán `docs/khao-sat/cau-hoi-google-form.md` vào Google Form, gửi nhóm lớp/khoa, mỗi
   người nhờ 8–10 bạn để đủ ít nhất 30 câu trả lời. Điền số vào các chỗ **[Cần số liệu khảo sát]** trong
   `docs/report/SP1-phan-tich-su-can-thiet.md`.
   - Không thay khảo sát bằng dữ liệu tải từ Kaggle: đó là khảo sát của người khác, ở nước khác. Dùng
     được làm **số liệu tham khảo bổ sung** (ghi rõ nguồn), ví dụ:
     [College Time Management — IEEE DataPort](https://ieee-dataport.org/documents/college-time-managment)
     (1.000 bản ghi: giờ học, trì hoãn, xao nhãng…),
     [Social media & productivity — Mendeley Data](https://data.mendeley.com/datasets/zv45t3hx2r/1)
     (1.501 sinh viên ở Dhaka). Đọc giấy phép trước khi dùng.
2. **Nhật ký AI (SP3):** mỗi người tự viết các mục *Nhận xét, đánh giá*, *Nội dung chỉnh sửa hoặc loại bỏ*,
   *Cách kiểm chứng* trong mọi nhật ký của mình, và **đính kèm lịch sử hội thoại gốc** (đề bài yêu cầu
   "phản hồi đầy đủ"; nhiều nhật ký hiện chỉ tóm tắt). Câu hỏi gợi ý để tự viết:
   - AI đề xuất gì mà mình **không dùng**, vì sao?
   - Mình phát hiện AI sai ở đâu, bằng cách nào (chạy test, đọc tài liệu gốc, thử trên app)?
   - Mình phải sửa gì sau khi AI viết?
3. **Đọc lại và sửa bằng lời mình:** SP1, SP2 mục 4–7 (nháp của Claude, đã đánh dấu trong file).
4. **Tổng duyệt demo** theo `docs/demo-kich-ban.md` (cần `GEMINI_API_KEY`), ít nhất 1 lần trên máy khác
   cài từ đầu theo README; ghi kết quả vào SP2 mục 6.3.

## Long

- `ai-log/AI-002-long-claude-code.md`: viết hai chỗ *[Long tự viết]*.
- Ghi nhật ký cho các phiên dùng Claude từ 09/11 đến 22/11 (nên tách thành AI-003, AI-004…). Tư liệu
  có thật để viết (bản xuất hội thoại gốc: xuất lại từ Claude Code, **không commit** vì có thông tin
  tài khoản):

  | Ngày | Việc nhờ Claude | Đã kiểm chứng bằng |
  |---|---|---|
  | 09–11/11 | Review và sửa PR #3–#7 (D chặn mặc định SUSPICIOUS, A từ chối trích dẫn thiếu bằng chứng, CI cài được) | `pytest`, chạy CI trên GitHub |
  | 11/11 | Mở rộng CI toàn repo, dọn 15 lỗi lint; sửa lỗi lọc tên tệp chỉ sai trên Linux | CI xanh trên Linux |
  | 15/11 | CP-SAT không bao giờ tệ hơn EDF (sửa test chập chờn); khôi phục code D sau revert | Chạy test C 6 lần liền; CI |
  | 20/11 | Nối B → C và D → B, merge PR #11, #12 | Test đi trọn đường D → B → C; CI |
  | 22/11 | Merge PR #14, #15, gộp hai cách nối D → A; nháp SP1, SP2 mục 4–7, kịch bản demo | `pytest` 656 test; chạy 3 email demo qua D |
  | 11–22/11 | Cập nhật tiến độ, nội dung task CoReach | Đối chiếu với GitHub |

  Ghi rõ những gì **không theo** Claude hoặc phải sửa lại (ví dụ: Claude nói Nam "chậm" dựa trên commit
  rồi phải đính chính khi Nam đẩy code; con số trong báo cáo phải đối chiếu lại).
- `docs/report/C-lap-lich.md`: 3 chỗ *[Cần kiểm chứng]* (nguồn EDF, nhận định PuLP chậm hơn, trang giá
  Motion).
- Thử thật: bot Telegram ("Gửi tin thử") và nhập file `.ics` vào Google Calendar.

## Duy (B)

- **Số đo B:** chạy `python -m eval.run_eval` với Gemini thật trên 20 mẫu `eval/gold`, ghi kết quả vào
  `docs/report/B-trich-xuat.md` và SP2 mục 6.2. Ghi đúng là **20 email tự soạn**, không phải "thực tế".
- **AI-B001:** sửa "20 mẫu thực tế" (dòng 15) và các số test không khớp (dòng 7 "73/73", dòng 10
  "179/179").
- **CR-01..03:** chốt với nhóm, ghi kết quả vào spec.
- **B.6 trong báo cáo B:** Todoist nay có "Email Assist" (gói trả phí) biến email chuyển tiếp thành việc
  kèm hạn — câu "phụ thuộc hoàn toàn vào nhập liệu thủ công" cần sửa
  ([Todoist Assist](https://www.todoist.com/help/articles/introduction-to-todoist-assist-KgPP22q5O)).

## Minh (D)

- **Số đo trên email thật hoặc bộ công khai:** hiện chỉ có 60 email tự tạo, và F1 của LLM (0,048) đo
  bằng LLM giả → chạy lại `eval/eval_module_d.py` với `LLM_PROVIDER=gemini`. Có thể thêm bộ phishing
  công khai (tiếng Anh) để đo riêng phần phát hiện lừa đảo, ghi rõ khác ngôn ngữ:
  [Phishing Email Detection (Kaggle, bản sao trên Hugging Face, LGPL-3.0)](https://huggingface.co/datasets/zefang-liu/phishing-email-dataset/blob/main/README.md),
  [Phishing Email Dataset — Naser Abdullah Alam (gộp Enron, CEAS, Nazario, SpamAssassin…)](https://baselight.app/u/kaggle/dataset/naserabdullahalam_phishing_email_dataset).
- Viết phần D trong SP2 nếu muốn bổ sung ngoài mục 6.2.

## Nam (A)

- Rà soát thủ công gold answer của bộ 30 câu (báo cáo A tự ghi `qa_24` chưa đối chiếu).
- Đã commit bộ câu hỏi có trích nguyên văn giáo trình Kinh tế chính trị — xác nhận việc trích ngắn này
  chấp nhận được (`.gitignore` từng chặn `benchmarks/qa/dataset.jsonl`).
- Kiểm tra trang Hỏi đáp sau khi gộp (22/11): giờ lấy tệp qua handoff chung của D, vẫn kiểm tra SHA-256
  bằng hàm của Nam (`read_verified_attachment`), vẫn không cho tải thẳng.
