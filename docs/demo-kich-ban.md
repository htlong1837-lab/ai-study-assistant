# Kịch bản demo (khoảng 10 phút)

*Nháp do Claude soạn ngày 22/11. Tổng duyệt ít nhất 1 lần trên máy dùng để báo cáo, và 1 lần trên một
máy khác cài từ đầu theo README.*

## Chuẩn bị (trước buổi demo)

```bash
git pull origin main
pip install -r requirements.txt
python -m scripts.make_demo_emails
```

1. Xoá CSDL cũ để task mẫu không lẫn vào luồng thật: xoá `data/app.db`.
2. `.env`: có `GEMINI_API_KEY` thì B trích bằng LLM và trang Hỏi đáp trả lời được; không có khóa thì
   B tự dùng bộ trích xuất theo luật (vẫn ra nhiệm vụ cho email mẫu), chỉ phần hỏi đáp không chạy.
   Có `VIRUSTOTAL_API_KEY` thì D tra thêm VirusTotal, không có vẫn chạy.
3. `streamlit run app.py`. Chuẩn bị sẵn file `data/demo/*.eml` (3 email tự soạn) và
   `data/sample/thoi_khoa_bieu.csv`.
4. Mở trước trang chủ; tắt thông báo máy.

## Các bước

Đã chạy thử trọn bước 1–6 và 9 trên app ngày 25/11, không có khóa API (B dùng bộ trích xuất theo luật). Bước 2 chạy thử với D (22/11): `01`, `02` ra *bài tập / an toàn*; `03` ra *lừa đảo / độc hại*, tệp bị chặn, link `bit.ly` nghi ngờ. Các bước 3–10 là kỳ vọng theo code, phải kiểm tra trong buổi tổng duyệt (bước 4–8 cần Gemini thật).

| # | Người nói | Trang | Thao tác | Điều cần thấy (kỳ vọng) | Ý cần nói |
|---|---|---|---|---|---|
| 1 | Long | Trang chủ | Giới thiệu luồng | Sơ đồ D → B → C, D → A | Vấn đề: bài tập phân tán, hạn tiếng Việt, email độc. AI chỉ đề xuất |
| 2 | Minh | Email & bảo mật | Bấm "✨ Thử với email mẫu" (hoặc tải 3 file `data/demo/*.eml`) | `01` và `02`: nhãn bài tập, an toàn. `03`: lừa đảo, **độc hại** — link `bit.ly` nghi ngờ, tệp `.pdf` thật ra là `.exe` | Cổng chặn: email độc không bao giờ sang A/B; tệp chỉ tra VirusTotal bằng SHA-256, không tải lên |
| 3 | Minh | Email & bảo mật | Bấm "Chuyển sang B/A" cho `01` và `02` | Báo đã chuyển; `03` không có nút chuyển | Người dùng quyết định chuyển tiếp |
| 4 | Duy | Trích xuất | Thấy 2 email từ D; bấm "Bắt đầu trích xuất" | Đề xuất "Bài tập lớn số 2", hạn 05/12 kèm câu trích; email dời hạn tạo **đề xuất cập nhật** hạn 12/12 | Chuẩn hoá ngày giờ tiếng Việt; câu trích phải có thật trong email; phát hiện thay đổi |
| 5 | Duy | Trích xuất | Chấp nhận đề xuất dời hạn, xác nhận nhiệm vụ | Nhiệm vụ chuyển sang "đã xác nhận" | AI chỉ đề xuất — người dùng xác nhận |
| 6 | Nam | Hỏi đáp | Chọn `de_bai_BTL2.pdf` (từ Module D) | Báo "đã qua cổng Module D"; trình đọc PDF | Chỉ nhận tệp đã quét, kiểm tra SHA-256 |
| 7 | Nam | Hỏi đáp | Hỏi "Tiêu chí chấm gồm những gì?" rồi bôi đen "Hạn nộp…" và hỏi | Trả lời kèm trích dẫn trang 1 | Trích dẫn được kiểm chứng; không có căn cứ thì từ chối |
| 8 | Nam | Hỏi đáp | Hỏi câu không có trong đề ("Thầy cho điểm cộng không?") | Từ chối trả lời | Benchmark Gemini thật: từ chối đúng 6/6 |
| 9 | Long | Lập lịch | Thấy nhiệm vụ của B đã tích; chọn "So sánh cả hai", bấm xếp | Lịch tuần quanh thời khoá biểu, bảng so sánh EDF / CP-SAT | Thí nghiệm 3 kịch bản × 10 seed |
| 10 | Long | Lập lịch | Tải file `.ics` | File lịch nhập được vào Google Calendar | Nhắc nhở qua `.ics`/Telegram |
| 11 | Long | — | Kết | — | Hạn chế: dữ liệu đánh giá B, D chưa phải email thật; hướng phát triển |

## Nếu có sự cố

- **Không có mạng/khóa API:** đặt `LLM_PROVIDER=fake`; bước 4 sẽ không trích ra nhiệm vụ → dùng
  4 nhiệm vụ mẫu (không xoá `data/app.db`) và nói rõ là dữ liệu mẫu.
- **Gemini chậm:** câu hỏi ở bước 7 có thể mất 10–30 giây (p95 đo được tới 33 giây), nói trong lúc chờ.
- **Lỗi trang:** `pytest tests/test_pages.py` trước buổi demo để chắc 5 trang mở được.

## Sau tổng duyệt

Ghi lại vào mục 6.3 của SP2: các bước đã chạy được, thời gian, lỗi gặp và cách xử lý.
