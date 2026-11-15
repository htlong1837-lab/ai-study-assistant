# Nhật ký sử dụng AI - Tương tác AI-D004

| Trường thông tin | Nội dung |
| :--- | :--- |
| **Mã tương tác** | AI-D004 |
| **Thời gian** | 11/11/2026, 10:15 |
| **Công cụ AI** | Google Antigravity (VS Code Extension) |
| **Mục đích** | Triển khai bộ phân loại email WP-02a, WP-02b (TF-IDF + Logistic Regression), WP-03 (LLM Zero-shot) và WP-04 (Thực nghiệm so sánh Macro-F1). |
| **Prompt đầy đủ** | `Dựa trên @docs/plan_module_d.md, hãy triển khai trọn gói Phần 2, 3, 4 (WP-02a, WP-02b, WP-03, WP-04) theo việc của Module D:

1. Tạo dữ liệu mẫu: data/emails_labeled.jsonl
   - Tạo ít nhất 40 mẫu email học tập bằng tiếng Việt phân bố đủ 4 nhãn: coursework (bài tập, hạn nộp), announcement (lịch thi, thông báo), phishing (lừa đảo, đe dọa khóa tài khoản), other (linh tinh). Định dạng JSONL: {"text": "...", "label": "..."}.

2. WP-02b (Baseline Classifier): modules/email_security/classifier/tfidf_lr.py
   - Xây dựng BaselineClassifier dùng FeatureUnion kết hợp word n-gram (1, 2) và char_wb (2, 4) qua TfidfVectorizer, phân loại bằng LogisticRegression(class_weight='balanced', max_iter=200).
   - Hàm train_from_file(jsonl_path).
   - Hàm predict(text) -> tuple[EmailLabel, float] trả về nhãn chuẩn theo core.contracts.EmailLabel và điểm confidence.

3. WP-03 (LLM Classifier): modules/email_security/classifier/llm_zeroshot.py
   - Xây dựng LLMZeroShotClassifier dùng core.llm_client.LLMClient.
   - Hàm predict(text) -> tuple[EmailLabel, float]. Bắt buộc bọc nội dung email bên trong thẻ an toàn <email>...</email> để phòng chống Prompt Injection.
   - Trả về EmailLabel tương ứng và fallback an toàn sang EmailLabel.OTHER nếu có lỗi hoặc mất kết nối mạng.

4. WP-04 (Thực nghiệm & So sánh): modules/email_security/classifier/compare.py
   - Viết hàm run_comparison(dataset_path) chạy 5-fold Cross Validation trên dữ liệu, in báo cáo classification_report (Precision, Recall, Macro-F1) cho Baseline TF-IDF + LR và đo thời gian inference mẫu của LLM Zero-shot.
   - Xuất kết quả tóm tắt ra file Markdown docs/email_classifier_comparison.md làm số liệu cho Báo cáo SP2.

5. Test tự động: tests/email_security/test_classifier.py
   - Viết các test case pytest kiểm thử hoạt động của BaselineClassifier và LLMZeroShotClassifier (dùng mock LLMClient để đảm bảo test chạy offline 100%).

Yêu cầu: Code sạch, type hint đầy đủ Python 3.11+, tuân thủ core/contracts.py, không dùng thư viện ngoài danh mục requirements.txt.` |
| **Phản hồi đầy đủ** | Sinh các file mã nguồn: `data/emails_labeled.jsonl`, `modules/email_security/classifier/tfidf_lr.py`, `modules/email_security/classifier/llm_zeroshot.py`, `modules/email_security/classifier/compare.py`, `tests/email_security/test_classifier.py` và tài liệu đối sánh `docs/email_classifier_comparison.md`. |
| **Nhận xét, đánh giá** | - **Ưu điểm:** Khởi tạo cấu trúc Pipeline Scikit-learn chuẩn với FeatureUnion bắt tốt tiếng Việt; prompt LLM có bọc thẻ XML `<email>` chống injection.<br>- **Hạn chế:** Bộ dữ liệu ban đầu 40 mẫu hơi nhỏ, cần mở rộng dần lên 300 mẫu ở các tuần tiếp theo. |
| **Nội dung được sử dụng** | Tiếp thu toàn bộ logic phân loại n-gram TF-IDF + Logistic Regression, hàm gọi LLM phân loại bọc XML và script chạy 5-fold CV. |
| **Nội dung chỉnh sửa hoặc loại bỏ** | Tự sửa lại hàm fallback trong `llm_zeroshot.py` để bắt thêm ngoại lệ `TimeoutError` và bổ sung mock cho bài test để pass 100% khi ngắt mạng. |
| **Cách kiểm chứng** | 1. Tự chạy `python -m modules.email_security.classifier.compare` kiểm tra bảng F1.<br>2. Chạy `pytest tests/email_security/test_classifier.py -v` xác nhận tất cả test case đều passed offline. |
| **Kết quả áp dụng** | Hoàn thành thực nghiệm và mã nguồn cho WP-02, WP-03, WP-04; có bảng số liệu Macro-F1 sẵn sàng đưa vào Báo cáo SP2. |