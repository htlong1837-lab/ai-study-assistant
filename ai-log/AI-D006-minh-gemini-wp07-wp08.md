# Nhật ký sử dụng AI — AI-D006

| Trường thông tin | Nội dung |
| :--- | :--- |
| **Mã tương tác** | AI-D006 |
| **Thời gian** | 16/11/2026 |
| **Thành viên thực hiện** | Hoàng Minh (Module D – Email & Bảo mật) |
| **Công cụ AI** | Gemini |
| **Mục đích** | Thiết kế, sinh mã nguồn triển khai và kiểm thử cho WP-08 (quét tệp đính kèm bằng SHA-256, phần mở rộng, magic bytes, kiểm tra nội dung ZIP) và WP-07 (tích hợp VirusTotal v3 API kèm bộ nhớ đệm SQLite và giới hạn tốc độ gọi API). |

---

## 1. Nội dung tương tác (Prompt & Phản hồi)

### Prompt đầy đủ
> Đọc kỹ docs/plan_module_d.md, core/contracts.py và modules/email_security/models.py.
Triển khai WP-08: Quét an toàn file đính kèm trong `modules/email_security/attachment_scanner.py` kèm unit tests đầy đủ trong `tests/email_security/test_attachment_scanner.py`:

1. Quy tắc kiểm tra tĩnh (Heuristic & Magic Bytes):
   - Tính mã băm SHA-256 (64 ký tự hex chữ thường, khớp regex `^[0-9a-f]{64}$` của `SafeAttachment` trong `core/contracts.py`).
   - Chặn ngay (`SafetyStatus.MALICIOUS`) nếu phần mở rộng (kể cả phần mở rộng kép như `baitap.pdf.exe`) thuộc nhóm nguy hiểm: `.exe`, `.bat`, `.cmd`, `.com`, `.scr`, `.pif`, `.vbs`, `.vbe`, `.js`, `.jse`, `.wsf`, `.wsh`, `.ps1`, `.msi`, `.msp`, `.hta`, `.cpl`, `.jar`, `.reg`, `.lnk`, `.dll`, `.sys`.
   - Kiểm tra Magic Bytes đầu file:
     * Nếu file bắt đầu bằng `MZ` (`b"\x4d\x5a"` - PE executable), ELF (`b"\x7fELF"`), hoặc Mach-O (`b"\xcf\xfa\xed\xfe"`, `b"\xfe\xed\xfa\xcf"`) -> Gắn `SafetyStatus.MALICIOUS` (đặc biệt cảnh báo giả mạo nếu tên file kết thúc bằng `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.txt`, `.jpg`, `.png`).
     * Nếu tên file là `.pdf` nhưng 5 byte đầu không phải `b"%PDF-"` -> Gắn `SafetyStatus.SUSPICIOUS` (sai định dạng header).
   - Nếu file `.zip`: kiểm tra danh sách file bên trong bằng `zipfile` (thư viện chuẩn); nếu chứa bất kỳ file thực thi nguy hiểm nào -> `SafetyStatus.MALICIOUS`; nếu file nén có mật khẩu -> `SafetyStatus.SUSPICIOUS`.
   - Các định dạng tài liệu/hình ảnh hợp lệ (`.pdf`, `.docx`, `.xlsx`, `.pptx`, `.txt`, `.csv`, `.png`, `.jpg`, `.jpeg`, `.zip` sạch) -> Gắn `SafetyStatus.SAFE`.

2. Đầu ra & Quy tắc "Chặn tại cổng":
   - Trả về dataclass `AttachmentScanResult` gồm: `filename`, `file_path`, `sha256`, `status: SafetyStatus`, `reasons: list[str]`, `safe_attachment: SafeAttachment | None`.
   - Tuân thủ tuyệt đối quy tắc "Chặn tại cổng": chỉ tạo object `SafeAttachment` (để chuyển sang Module A) khi `status == SafetyStatus.SAFE` (hoặc `SUSPICIOUS` khi có cờ `allow_suspicious=True`); tuyệt đối trả về `None` nếu `MALICIOUS`.

3. Kiểm thử & Chất lượng code:
   - Viết unit tests trong `tests/email_security/test_attachment_scanner.py` bao phủ mọi nhánh (file sạch, PDF thật, EXE giả danh PDF bằng magic bytes `MZ`, đuôi kép `.pdf.exe`, file ZIP chứa `.bat`, file ZIP đặt mật khẩu, file không tồn tại).
   - Chạy `pytest` và `ruff check .` đảm bảo pass 100%, không làm hỏng các test cũ.

   Đọc kỹ docs/plan_module_d.md, core/config.py, core/contracts.py, modules/email_security/url_scanner.py và modules/email_security/attachment_scanner.py.
Triển khai WP-07: Tích hợp VirusTotal v3 API và bộ nhớ đệm SQLite trong `modules/email_security/virustotal.py` kèm unit tests đầy đủ trong `tests/email_security/test_virustotal.py`:

1. Kiến trúc & Quản lý khóa API:
   - Đọc `VIRUSTOTAL_API_KEY` từ biến môi trường (`.env` / `os.getenv`). Nếu chưa cấu hình API key, hệ thống không crash mà tự động fallback về kết quả của bộ lọc heuristic trước đó kèm ghi chú trong `reasons`.
   - Chỉ sử dụng thư viện chuẩn (`urllib.request`, `sqlite3`, `base64`, `hashlib`, `time`, `json`) hoặc thư viện đã có sẵn trong `requirements.txt`, không tự ý cài thêm thư viện ngoài.

2. Bộ nhớ đệm SQLite (`vt_cache.sqlite`) & Rate Limit:
   - Lưu cache kết quả tra cứu vào SQLite (mặc định `data/vt_cache.sqlite`, cho phép truyền `db_path=":memory:"` khi test) theo khóa `(resource_type, resource_key)` với `resource_type` là `"url"` hoặc `"sha256"`, kèm `malicious_count`, `suspicious_count`, `harmless_count`, `checked_at`.
   - Hỗ trợ TTL (thời gian sống của cache, mặc định 24 giờ) để tránh gọi lại API trùng lặp.
   - Tích hợp Rate Limiter giới hạn tối đa 4 request/phút (tuân thủ giới hạn gói miễn phí VirusTotal) với tùy chọn tắt delay khi chạy unit test.

3. Quy tắc tra cứu "Heuristic chạy trước, chỉ tra VirusTotal khi nghi ngờ":
   - Cung cấp 2 hàm chính:
     * `lookup_url_reputation(url: str, ...)` (gọi endpoint `GET https://www.virustotal.com/api/v3/urls/{url_id}` với `url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")`).
     * `lookup_file_hash(sha256: str, ...)` (gọi endpoint `GET https://www.virustotal.com/api/v3/files/{sha256}`).
   - Quy đổi số lượng engine phát hiện (`last_analysis_stats`) sang `SafetyStatus`:
     * `malicious >= 2` -> `SafetyStatus.MALICIOUS`
     * `malicious == 1` or `suspicious >= 1` -> `SafetyStatus.SUSPICIOUS`
     * ngược lại -> `SafetyStatus.SAFE`
   - Viết hàm kết hợp `verify_url_with_vt(heuristic_result, ...)` và `verify_attachment_with_vt(scan_result, ...)`: chỉ gọi VirusTotal API khi kết quả heuristic đang ở trạng thái `SafetyStatus.SUSPICIOUS` (bỏ qua nếu đã `SAFE` hoặc `MALICIOUS`, trừ khi bật `force_vt=True`).

4. Kiểm thử & Chất lượng code:
   - Viết unit tests trong `tests/email_security/test_virustotal.py` sử dụng `unittest.mock.patch` để giả lập phản hồi API VirusTotal (clean, suspicious, malicious, lỗi mạng/HTTP 429, thiếu API key) và kiểm tra cơ chế cache hit/miss trên SQLite `:memory:`.
   - Chạy `pytest` và `ruff check .` đảm bảo toàn bộ repo pass 100%.

### Phản hồi đầy đủ từ AI
AI đã đề xuất mã nguồn Python hoàn chỉnh cho hai mô-đun:
1. **`modules/email_security/attachment_scanner.py` (WP-08):**
   - Hàm `compute_sha256()` tính mã băm SHA-256 (64 ký tự hex chữ thường) khớp chuẩn kiểm tra định dạng của `SafeAttachment` trong `core/contracts.py`.
   - Bộ lọc tĩnh kiểm tra phần mở rộng nguy hiểm (`DANGEROUS_EXTENSIONS` gồm `.exe`, `.bat`, `.ps1`, `.vbs`, `.js`, `.jar`, `.dll`... bao gồm cả phần mở rộng kép như `baitap.pdf.exe`).
   - Bộ kiểm tra Magic Bytes đầu tệp (`EXECUTABLE_MAGIC_SIGNATURES` nhận diện `MZ` của Windows PE, `\x7fELF` của Linux và Mach-O của macOS) để phát hiện tệp thực thi giả mạo tài liệu `.pdf`/`.docx`/`.xlsx`, đồng thời kiểm tra chữ ký chuẩn `%PDF-` cho tệp `.pdf`.
   - Hàm `_inspect_zip()` dùng thư viện chuẩn `zipfile` để rà soát tệp thực thi ẩn bên trong file nén `.zip` hoặc cảnh báo file nén đặt mật khẩu.
   - Thực thi quy tắc **Chặn tại cổng**: chỉ trả về đối tượng `SafeAttachment` khi trạng thái là `SAFE` (hoặc `SUSPICIOUS` nếu bật cờ `allow_suspicious=True`), tuyệt đối trả về `None` nếu `MALICIOUS`.
2. **`modules/email_security/virustotal.py` (WP-07):**
   - Lớp `VirusTotalClient` đọc `VIRUSTOTAL_API_KEY` từ biến môi trường, sử dụng thư viện chuẩn `urllib.request`, `sqlite3`, `base64`, `time`.
   - Lưu bộ nhớ đệm (cache) vào cơ sở dữ liệu SQLite (`data/vt_cache.sqlite`) theo cặp khóa `(resource_type, resource_key)` (`url` hoặc `sha256`) kèm thời gian sống (TTL mặc định 24 giờ) để tránh gọi trùng lặp.
   - Cơ chế giới hạn tần suất gọi API (`min_interval_seconds = 15.0`, tương đương tối đa 4 lượt/phút theo hạn mức gói miễn phí của VirusTotal).
   - Hàm `verify_attachment_with_vt()` thực hiện nguyên tắc *heuristic chạy trước, chỉ tra VirusTotal khi ở trạng thái `SUSPICIOUS`*, tự động fallback an toàn nếu chưa cấu hình API key hoặc gặp lỗi mạng/HTTP.

---

## 2. Nhận xét, đánh giá và kiểm chứng

| Hạng mục | Chi tiết |
| :--- | :--- |
| **Nhận xét, đánh giá** | Mã nguồn AI sinh ra sạch, bám sát hợp đồng dữ liệu `SafeAttachment` và `SafetyStatus` trong `core/contracts.py`. Việc dùng hoàn toàn thư viện chuẩn của Python (`hashlib`, `zipfile`, `sqlite3`, `urllib.request`) giúp không phát sinh thêm thư viện ngoài trong `requirements.txt` và giữ ứng dụng gọn nhẹ. |
| **Nội dung được sử dụng** | Giữ lại toàn bộ kiến trúc hàm băm SHA-256, bảng chữ ký magic bytes (`MZ`, `ELF`, `Mach-O`), logic kiểm tra tệp ZIP, cấu trúc bảng cache `vt_cache` trên SQLite và luồng chỉ tra cứu VirusTotal khi kết quả tĩnh là `SUSPICIOUS`. |
| **Nội dung chỉnh sửa hoặc loại bỏ** | - Kiểm tra và rà soát lại các tham số mặc định (đường dẫn `DEFAULT_VT_DB_PATH = Path("data/vt_cache.sqlite")`) để đảm bảo thư mục `data/` không đẩy dữ liệu cache thật lên Git (đã có trong `.gitignore`).<br>- Bổ sung thêm hàm kết hợp `verify_url_with_vt()` (nối kết quả từ `url_scanner.py` của WP-06 sang `VirusTotalClient.lookup_url()`) để hoàn thiện luồng quét liên kết. |
| **Cách kiểm chứng** | - Chạy bộ kiểm thử đơn vị (`pytest tests/email_security/test_attachment_scanner.py tests/email_security/test_virustotal.py`) với các kịch bản giả lập (tệp PDF hợp lệ, tệp `.exe` đổi đuôi thành `.pdf` nhưng giữ header `MZ`, tệp ZIP chứa `.bat`, giả lập phản hồi API VirusTotal bằng `unittest.mock.patch`, kiểm tra cache hit/miss trên SQLite `:memory:`).<br>- Chạy công cụ kiểm tra định dạng và lỗi tĩnh `ruff check .` và `ruff format --check .` để đảm bảo đạt chuẩn CI của nhóm. |
| **Kết quả áp dụng** | Đã tích hợp vào `modules/email_security/attachment_scanner.py` và `modules/email_security/virustotal.py`, sẵn sàng nối vào luồng xử lý tổng của Module D và giao diện `views/email_security.py`. |