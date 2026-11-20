# A — Hỏi đáp tài liệu

## Cách làm và luồng an toàn

Module D chuyển `SafeAttachment` sau khi email được phép chuyển tiếp. Trang Q&A chỉ nhận kiểu dữ liệu này, xác minh SHA-256 khi đọc file rồi dùng parser của Module A để tạo `ParsedDocument`. Upload trực tiếp PDF/TXT/Markdown trên trang Q&A đã bị tắt; tài liệu phải đi qua D trước.

PDF được phân tích trong worker riêng có timeout. Câu trả lời chỉ được hiển thị khi trích dẫn vượt qua bước kiểm chứng nguồn; nội dung không có căn cứ được xử lý theo cơ chế từ chối của QA.

## Kiểm chứng trích dẫn

Runner kiểm tra các trang và bằng chứng chuẩn có trong PDF nguồn trước khi gọi Gemini. Ở bước đánh giá, citation verifier kiểm tra trích dẫn của câu trả lời có nguyên văn trong tài liệu hay không. Chỉ số này khác với mức khớp bằng chứng chuẩn của từng câu.

## Benchmark Gemini thật

Lần chạy ngày 19/11/2026 dùng model `gemini-3.5-flash-lite`, dataset 30 câu và PDF nguồn được lưu cục bộ. Cả 30 câu đã được gửi chạy: 29 câu có kết quả trả lời được đưa vào thống kê; `qa_08` bị citation verifier từ chối vì hai citation do mô hình sinh ra không tìm thấy trong ngữ cảnh tài liệu (`CITATION_NOT_FOUND`). Đây là một lần chạy có lỗi chất lượng đầu ra, không phải lỗi cấu trúc hoặc bằng chứng chuẩn của bản ghi.

| Loại câu | Kết quả | Exact match | Page hit | Khớp gold evidence | Citation verifier | Latency p50 / p95 |
|---|---:|---:|---:|---:|---:|---:|
| Toàn tài liệu | 11/12 có câu trả lời được chấp nhận; 1/12 bị từ chối do citation | 0% | 90,91% | 86,36% | 100% | 7,88 / 33,21 giây |
| Theo đoạn | 12/12 hoàn tất | 0% | 95,83% | 20,83% | 100% | 4,46 / 79,34 giây |
| Không thể trả lời | 6/6 hoàn tất; từ chối đúng 6/6 | — | — | — | — | 7,42 / 11,72 giây |

Exact match là so khớp nguyên văn sau chuẩn hóa, không đo tương đương ngữ nghĩa. `citation_verbatim_record_rate` 100% nghĩa là citation được verifier xác nhận có trong tài liệu; không có nghĩa citation luôn trùng với gold evidence. Chi phí là `null` vì chưa đo.

Các số liệu trên là kết quả của đúng phiên bản dataset tại thời điểm chạy. Benchmark đã thử đủ 30 bản ghi, nhưng chỉ 29 bản ghi tạo được câu trả lời được đánh giá; Q8 được tính là citation failure, không được tính như câu trả lời thành công. Các tỷ lệ trong bảng phản ánh các câu trả lời được chấp nhận; riêng nhóm toàn tài liệu có 11 kết quả được chấp nhận trên 12 câu đã thử. Validator xác nhận cấu trúc và việc đoạn trích chuẩn có trong PDF, nhưng không xác nhận đáp án chuẩn đúng về nội dung. Cần con người rà soát gold answer; ghi chú của `qa_24` hiện vẫn nói đáp án chưa được đối chiếu thủ công. Vì vậy đây là kết quả benchmark thực tế của lần chạy, chưa phải bộ gold đã được xác nhận thủ công hoặc kết quả pass toàn bộ.

## Giới hạn

OCR cho PDF scan và xác minh luồng đầu-cuối trên trình duyệt vẫn cần kiểm tra riêng. Dataset cần được người phụ trách xác nhận; không dùng kết quả từ template hoặc dữ liệu chưa review làm số liệu cuối.


