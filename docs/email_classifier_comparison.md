# Báo cáo So sánh Classifier — Module D Email & Bảo mật

> **Ngày tạo:** 2026-11-11 10:14  
> **Dataset:** `data\emails_labeled.jsonl` (44 mẫu)  
> **Phương pháp đánh giá:** Stratified 5-Fold Cross Validation

---

## 1. Baseline — TF-IDF (word + char\_wb) + Logistic Regression

### Kết quả Cross Validation (5 fold)

| Chỉ số | Giá trị |
|---|---|
| **Macro-F1 trung bình** | **0.8602** |
| Độ lệch chuẩn Macro-F1 | ±0.1350 |
| F1 từng fold | 1.0000, 0.6429, 1.0000, 0.7917, 0.8667 |
| Thời gian inference TB | 0.385 ms/mẫu |

### Classification Report (tích lũy 5 fold)

```
              precision    recall  f1-score   support

announcement       0.71      0.91      0.80        11
  coursework       0.92      1.00      0.96        11
       other       0.88      0.64      0.74        11
    phishing       1.00      0.91      0.95        11

    accuracy                           0.86        44
   macro avg       0.88      0.86      0.86        44
weighted avg       0.88      0.86      0.86        44

```

---

## 2. LLM Zero-Shot (Gemini / fake)

> **Lưu ý:** Đo thời gian trên `LLM_PROVIDER=fake` (offline).  
> Với Gemini API thực tế, latency ≈ 500–2000 ms/request.

| Chỉ số | Giá trị |
|---|---|
| Số mẫu đo | 3 |
| Thời gian inference TB | 0.0 ms/mẫu (fake) |

#### Kết quả mẫu (fake LLM — không phản ánh chất lượng thực):

| Mẫu | Nhãn dự đoán | Confidence |
|---|---|---|
| 1 | other | 0.00 |
| 2 | other | 0.00 |
| 3 | other | 0.00 |

---

## 3. Phân tích & Quyết định

### So sánh tổng quan

| | Baseline TF-IDF+LR | LLM Zero-shot |
|---|---|---|
| Macro-F1 | 0.8602 ± 0.1350 | Chưa đánh giá CV (cần quota) |
| Inference | 0.38 ms/mẫu | ~500–2000 ms/mẫu |
| Phụ thuộc mạng | ❌ Không | ✅ Có (hoặc fake) |
| Chi phí | Miễn phí | Tốn API quota |
| Chạy offline | ✅ Hoàn toàn | ✅ Với `LLM_PROVIDER=fake` |

### Quyết định phương pháp production

**Chọn: Baseline TF-IDF+LR** làm phương pháp mặc định vì:

1. **Chạy offline hoàn toàn** — đảm bảo Constitution V (demo không phụ thuộc mạng).
2. **Nhanh hơn ~100x** — phù hợp xử lý batch nhiều email.
3. **Miễn phí** — không tốn API quota.
4. **Macro-F1 ≥ 0.86** trên dataset tổng hợp.

**LLM Zero-shot** được dùng làm:
- Fallback khi Baseline confidence < 0.6 (ensemble, WP-03).
- Phân loại trường hợp đặc biệt mà TF-IDF không đủ tín hiệu.

### Hạn chế & Hướng cải thiện

- Dataset hiện tại (44 mẫu) còn nhỏ — cần ≥ 300 mẫu để F1 có ý nghĩa thống kê (plan § A11).
- TF-IDF yếu với email viết tắt / không dấu — xem xét thêm bước chuẩn hoá.
- LLM cần đánh giá CV đầy đủ khi có quota (chạy `compare.py --with-llm`).

---

*Tạo tự động bởi `modules/email_security/classifier/compare.py` — Module D (Hoàng Minh)*
