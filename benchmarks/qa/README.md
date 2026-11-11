# QA Benchmark – tài liệu mẫu và đáp án chuẩn

## Kiểm tra dữ liệu bằng Codex

Template và validator nằm trong repo. Validator chỉ đọc JSONL; nó không gọi LLM và không tạo hoặc sửa nhãn vàng.

```powershell
Copy-Item benchmarks/qa/dataset.template.jsonl benchmarks/qa/dataset.jsonl
python scripts/validate_qa_benchmark.py
python scripts/validate_qa_benchmark.py --full
python scripts/run_qa_benchmark.py --pdf "C:/duong-dan-ca-nhan/giao-trinh.pdf"
```

Lệnh mặc định kiểm tra định dạng và liệt kê các dòng đang `needs_human_review: true`. `--full` yêu cầu đúng 30 dòng theo phân bố 12/12/6, toàn bộ dòng đã review, có đáp án/trang/evidence hợp lệ; lệnh trả mã lỗi nếu còn thiếu.

Với loại `passage`, runner sử dụng chính xác `passage_page` và `passage_text` đã được người đọc trích từ PDF. Nó từ chối chạy nếu đoạn/page không khớp tài liệu nguồn.

## Mục đích

Thư mục này là template để xây dựng benchmark QA từ PDF giáo trình **Kinh tế chính trị Mác - Lênin** mà bạn cung cấp. Template chỉ tạo khung dữ liệu; **không tự điền câu hỏi, đáp án hoặc trích dẫn**. Người đọc tài liệu phải xác nhận toàn bộ dữ liệu chuẩn.

## Cấu trúc

- `dataset.template.jsonl`: 30 bản ghi trống, chia thành:
  - `qa_01`–`qa_12`: 12 câu hỏi toàn tài liệu.
  - `qa_13`–`qa_24`: 12 câu hỏi theo đoạn.
  - `qa_25`–`qa_30`: 6 câu không thể trả lời từ tài liệu.
- `CODEX_TASK.md`: yêu cầu gửi Codex để triển khai runner và kiểm tra định dạng.
- `.gitignore`: mẫu loại trừ PDF có bản quyền và dataset/benchmark nội bộ nếu cần.

## Cách điền

Mỗi dòng trong JSONL là một JSON object độc lập. Không thêm dấu phẩy giữa các dòng.

| Trường | Cách điền |
|---|---|
| `id` | Giữ nguyên ID duy nhất. |
| `type` | Giữ nguyên một trong `whole_document`, `passage`, `unanswerable`. |
| `question` | Câu hỏi benchmark. |
| `gold_answer` | Đáp án chuẩn do người đọc xác nhận. |
| `gold_pages` | Mảng số trang PDF (đánh số từ 1) có thông tin hỗ trợ đáp án. |
| `gold_evidence` | Mảng trích dẫn nguyên văn ngắn từ PDF, tương ứng với trang trong `gold_pages`. |
| `passage_page` | Số trang PDF (từ 1), chỉ dùng với `passage`; loại khác để `null`. |
| `passage_text` | Đoạn nguyên văn được người dùng chọn, chỉ dùng với `passage`; loại khác để chuỗi rỗng. |
| `needs_human_review` | Để `true` cho đến khi người đọc đối chiếu và xác nhận; sau đó đổi thành `false`. |
| `review_notes` | Ghi chú khi rà soát, có thể để chuỗi rỗng. |

### Quy tắc theo loại câu hỏi

**`whole_document` (12 câu):**
- Hỏi về nội dung cần tổng hợp từ nhiều phần hoặc toàn tài liệu.
- Điền đáp án chuẩn, các trang hỗ trợ và trích dẫn nguyên văn.
- Không nhất thiết phải dùng tất cả các trang PDF.

**`passage` (12 câu):**
- Chọn một đoạn thực sự khó hiểu hoặc dễ bị diễn giải sai.
- Điền `passage_page` và `passage_text` để runner gọi đúng chế độ hỏi theo đoạn.
- `gold_pages` ghi trang chứa đoạn đó.
- `gold_evidence` chép nguyên văn phần đoạn làm căn cứ; không tự diễn đạt lại phần trích dẫn.
- `gold_answer` là câu trả lời chuẩn cho câu hỏi về đoạn đó.

**`unanswerable` (6 câu):**
- Hỏi một vấn đề gần chủ đề tài liệu nhưng tài liệu không đề cập.
- Để `gold_pages` và `gold_evidence` là mảng rỗng.
- `gold_answer` ghi rõ đây là câu hỏi không thể trả lời dựa trên tài liệu (ví dụ: `Không đủ thông tin trong tài liệu để trả lời.`).
- Không dùng kiến thức ngoài để tạo đáp án cho loại này.

## Lưu ý về PDF và trang

PDF được tải lên có 198 trang. Bạn không cần đưa cả cuốn vào benchmark: nên chọn một phần liên tục khoảng 15–30 trang hoặc trích xuất thành PDF mẫu riêng. Khi ghi `gold_pages`, thống nhất dùng **số trang PDF hiển thị trong trình đọc (bắt đầu từ 1)**, không trộn với số trang in trên chân trang sách. Nếu muốn dùng số trang in trong sách, hãy đổi quy ước nhất quán và ghi rõ trong README.

PDF giáo trình có thể có bản quyền. Không commit PDF lên repo nếu bạn không có quyền phân phối. Lưu PDF ở máy cá nhân hoặc vị trí dữ liệu riêng; cập nhật đường dẫn cục bộ trong cấu hình runner (nếu runner cần đường dẫn). Không đưa đường dẫn tuyệt đối của máy bạn vào repo dùng chung.

## Điều kiện hoàn tất dataset

- Có đủ 30 dòng JSONL hợp lệ.
- Đúng phân bổ 12/12/6.
- Mỗi câu có `question` không rỗng.
- Các câu `whole_document` và `passage` có đáp án, trang và evidence đã được người đọc xác nhận.
- Các câu `unanswerable` không có evidence/trang và đáp án thể hiện rõ không đủ căn cứ.
- Tất cả bản ghi đã được rà soát: `needs_human_review: false`.

## Chạy benchmark

1. Copy template thành `benchmarks/qa/dataset.jsonl` và tự điền/review gold fields, gồm `passage_page`/`passage_text`.
2. Chạy validator với `--full`; runner chặn việc chạy khi dataset chưa đúng 30 bản ghi, chưa đúng tỉ lệ 12/12/6 hoặc còn pending review.
3. Chạy `python scripts/run_qa_benchmark.py --pdf <đường-dẫn-PDF>` từ repo root. Runner yêu cầu Gemini API key bằng prompt ẩn, không ghi key vào report. File kết quả nằm trong `benchmarks/qa/results/` (đã gitignore); PDF và đáp án chuẩn không được đưa vào report.

Metrics gồm exact-match đã chuẩn hóa (so khớp literal, không phải judge ngữ nghĩa), page hit, khớp evidence chuẩn, citation verbatim, abstain precision, fallback rate và p50/p95 latency. Chi phí để `null` vì chưa xác minh bảng giá model.

**Quan trọng:** Codex chỉ nên xây runner, schema validation và báo lỗi dữ liệu thiếu/sai định dạng. Không yêu cầu Codex/AI tự sinh hoặc tự xác nhận gold answer.
