# Quyết định triển khai Module A

## 2026-11-10 — PDF.js đã vendor từ registry chính thức

Vendored `pdfjs-dist@6.4.299` theo yêu cầu người dùng, gồm ESM build, worker, viewer CSS/images, LICENSE và VERSION. Đọc đúng gói README và type declarations trước khi tích hợp `getDocument({data})` cùng `TextLayer({textContentSource, container, viewport}).render()`. PDF bytes chỉ truyền vào component khi document đổi hoặc iframe yêu cầu lại; API key không đưa vào component.

## 2026-11-10 — Cache câu trả lời QA chỉ trong session

QA gọi core với `use_cache=False` để tránh dùng cache file dùng chung. Kết quả `verified` được cache trong `st.session_state` theo tài liệu, phiên bản prompt, model và câu hỏi đã chuẩn hóa; cache không bao gồm API key, chỉ nhận câu trả lời đã xác minh và có giới hạn số mục. Mỗi người dùng/phiên có cache riêng và cache bị mất khi session kết thúc.

## 2026-11-10 — Logging QA có cấu trúc

Ghi metadata vận hành (doc/question ID, model, source, latency, trạng thái); không ghi văn bản câu hỏi, đoạn chọn, tài liệu hay key. Nội dung lỗi chỉ ghi loại exception sau khi che mẫu key.

## 2026-11-10 — Benchmark passage

Dataset giữ `passage_page` và `passage_text` cạnh câu hỏi để xác định đoạn nguồn được người dùng chọn. Các giá trị chuẩn vẫn do người dùng điền từ PDF thật; template không được tính là bộ benchmark đã review.

## 2026-11-11 — Timeout và retry theo loại lỗi

`LLMClient.generate()` nhận thêm tham số `timeout` tùy chọn; hành vi cũ của các module khác giữ nguyên. QA đặt timeout 60 giây, retry tối đa hai lần khi gặp timeout/deadline, lỗi kết nối/transport hoặc mã HTTP transient (408/429/5xx đã chọn), với backoff tăng dần. JSON sai schema được gửi lại một lần bằng prompt sửa có escape nội dung phản hồi. Không chuyển lỗi timeout sang câu trả lời fallback.

PDF được phân tích trong subprocess riêng bằng `python -m modules.qa.pdf_parse_worker`; dùng subprocess thay cho multiprocessing spawn trực tiếp để Windows không khởi chạy lại entrypoint Streamlit trong child process. Hết 60 giây, child process bị dừng và file tạm được xóa trong `finally`.

## 2026-11-11 — Giải phóng canvas ngoài vùng nhìn

Reader giữ placeholder cho các trang nhưng gỡ canvas và text layer khi trang ra khỏi vùng nhìn 500 px; khi quay lại, trang được render lại. PDF.js scripting và eval bị tắt. Browser profiling trên tài liệu dài vẫn cần checklist thủ công.

## 2026-11-11 — Xóa khóa QA khi rời trang trong app chung

`app.py` theo dõi route đang chọn và xóa `qa_api_key` cùng widget input khi chuyển khỏi trang QA. Đây là thay đổi nhỏ để đáp ứng kiểm tra vòng đời khóa ở Phase 5.2; các state key khác của app không bị động tới.

## 2026-11-10 — Không sửa `core/contracts.py`

Giữ metadata trạng thái trang ở lớp QA; giao diện dùng `ParsedDocument`/`Page` hiện có. Reader chia sẻ tài liệu hiện tại qua `modules.qa.api.get_current_document(session_state)`.
