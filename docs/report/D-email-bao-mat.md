# Báo cáo Module D — Email và Bảo mật

## Kiến trúc và cổng an toàn

`process_email` parse `.eml`, trích URL/tệp đính kèm, quét heuristic offline, tra VirusTotal cho mục `SUSPICIOUS` khi có API key, tổng hợp trạng thái rồi mới phân loại và tóm tắt. `SAFE < SUSPICIOUS < MALICIOUS`; phishing nâng email tối thiểu lên `SUSPICIOUS`. LLM chỉ ảnh hưởng nhãn/tóm tắt, không thể hạ trạng thái từ scanner. Email `MALICIOUS` không được chuyển; tệp độc không tạo `SafeAttachment`. Email `SUSPICIOUS` cần người dùng xác nhận và cổng `can_forward` vẫn từ chối `MALICIOUS`.

## Trích xuất và ẩn danh

Parser dùng thư viện `email` của Python, ưu tiên `text/plain`, trích link HTML và lưu tệp với tên đã làm sạch cùng SHA-256. Trước khi gửi nội dung email cho bộ phân loại zero-shot hoặc summarizer, `redact_pii` che email, số điện thoại Việt Nam và MSSV. Summary chỉ chạy cho email học tập `SAFE` và giới hạn 150 ký tự; lỗi LLM dùng fallback nội dung đã che PII.

## Bộ phân loại

TF-IDF kết hợp unigram/bigram và character n-gram với Logistic Regression là mặc định offline. Có thể chọn zero-shot bằng `EMAIL_CLASSIFIER=llm`; lỗi LLM rơi về TF-IDF. TF-IDF có độ trễ thấp, tái lập được và không cần mạng, nhưng phụ thuộc dữ liệu gán nhãn. Zero-shot tránh huấn luyện nhưng cần provider/API và kết quả phụ thuộc model/prompt. Bảng dưới dùng provider được cấu hình; `fake` chỉ đo đường fallback, không đại diện chất lượng LLM thật.

## Heuristic, VirusTotal v3 và cache

URL được chuẩn hóa trước khi tra; chỉ URL `SUSPICIOUS` được gửi tra cứu. Tệp chỉ được tra theo SHA-256, không upload nội dung. `VirusTotalClient` áp dụng giới hạn tần suất và cache SQLite TTL; lỗi/404 không được coi là xác nhận sạch. Kết quả sạch không được hạ tín hiệu heuristic hiện có. Khi thiếu key hoặc gặp lỗi, scanner giữ kết quả offline và trạng thái chưa đủ kết luận ở `SUSPICIOUS`.

## Kết quả đánh giá mô phỏng

Ngày chạy: 2026-11-17. Bộ dữ liệu mô phỏng ẩn danh gồm 60 email (10 mẫu mỗi nhãn: coursework, announcement, schedule, phishing, spam, other). Dữ liệu được lưu ở `eval/module_d_samples.jsonl`; đây là template mô phỏng, không phải email thu thập từ người dùng.

## Phân loại email

| Phương pháp | Macro-F1 | Ghi chú |
|---|---:|---|
| TF-IDF word/char + Logistic Regression (Stratified 5-fold) | 0.502 | Đánh giá out-of-fold |
| LLM zero-shot | 0.048 | Kết quả zero-shot theo provider cấu hình; fake không đại diện LLM thật. |

Phishing TF-IDF (precision 0.250, recall 0.300) được tính trên cùng bộ template mô phỏng; đây không phải ước lượng trên email thực tế.

## Phát hiện an toàn

| Tác vụ | Precision | Recall | Bộ kiểm tra |
|---|---:|---:|---|
| Email phishing | 0.250 | 0.300 | 60 email mô phỏng |
| URL độc/nghi ngờ | 1.000 | 1.000 | 60 URL kiểm tra |
| Tệp giả mạo/thực thi | 1.000 | 1.000 | 60 tệp tổng hợp |

Scanner URL/file đo theo bộ ca tổng hợp có nhãn kỳ vọng. VirusTotal không được gọi trong lần đánh giá này; kết quả heuristic offline được kiểm tra riêng.
