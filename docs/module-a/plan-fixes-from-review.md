# Plan fixes Module A — theo review PR 09/11/2026

> Trạng thái: các hạng mục trong plan đã hoàn tất. Key cũ trong `.env` đã được thu hồi; fixture lịch sử được người dùng xác nhận là dữ liệu giả.
> Căn cứ: review PR của Long ngày 09/11/2026 và trạng thái tài liệu Phase 0 hiện có trong repo.
> Phạm vi: xử lý blockers của review để đưa Module A vào kiến trúc chung và có thể kiểm thử từ repo root.

## Bối cảnh và cách đọc nguồn

- Review PR mô tả các vấn đề cần xác minh/sửa; chưa mặc định mọi nhận định trong review đúng với checkout hiện tại.
- `docs/module-a/plan-phase-0.md` đánh dấu 0.1–0.5 hoàn tất. Đây là trạng thái ghi trong tài liệu, chưa phải kết quả audit độc lập trong plan này.
- `PLAN_MODULE_A_FIXES.md` có nhiều kế hoạch Phase 1–4 và một số quyết định/giả định chưa được review PR xác nhận. Chúng không phải blockers của review này; chỉ đưa vào backlog sau khi đối chiếu code và nguồn chính thức. Không coi tên model, giá, tier, hay hành vi API nêu trong tài liệu là dữ kiện đã xác minh.
- Hạn ghi trong review là hết ngày 10/11/2026. Xác nhận lại mốc này nếu kế hoạch được dùng sau ngày đó.

## Mục tiêu hoàn tất

1. Không còn chuỗi có hình thức API key thật trong test/source; xác định an toàn liệu có credential thật từng được commit hay không và ghi rõ cách xử lý.
2. `pytest` chạy được từ repo root mà không cần đặt `PYTHONPATH`.
3. Module A dùng chung kiến trúc ứng dụng: logic trong `modules/qa/`, giao diện trong `views/qa.py`, app chung chạy qua `app.py`, document types dùng từ `core/contracts.py`, LLM dùng `core/llm_client.py`.
4. Bỏ dependency SDK cũ không còn dùng, sửa định danh spec bị trùng, và loại các script Specify dùng chung khỏi phạm vi Module A.
5. Có bằng chứng kiểm thử ở repo root và xác nhận trang QA mở được trong app chung.

## Thứ tự thực hiện

### A0 — Xác minh và xử lý chuỗi nghi là API key (ưu tiên đầu tiên)

**Nguồn review:** `tests/unit/test_api_key_lifecycle.py`, biến `fake_aiza`.

1. Kiểm tra dòng được review và các vị trí tương tự bằng tìm kiếm chỉ in tên file/vị trí, không in giá trị có thể là secret.
2. Thay chuỗi định dạng giống key bằng placeholder rõ ràng, không thể nhầm là credential thật (ví dụ `"FAKE_GOOGLE_API_KEY_FOR_TESTS"`). Cập nhật test để không cần chuỗi có hình dạng key hợp lệ.
3. Kiểm tra lịch sử Git bằng công cụ chỉ báo file/commit bị ảnh hưởng; không in giá trị key ra terminal, log hay báo cáo.
4. Nếu có bằng chứng key thật đã commit: báo người sở hữu thu hồi key ngay. Việc rewrite history chỉ làm theo quy trình nhóm và sau khi đánh giá ảnh hưởng tới các clone/nhánh; không tự rewrite history trong task này.
5. Ghi kết luận (credential thật/giả/chưa xác định), phạm vi đã quét và hành động tiếp theo vào verification log mà không ghi secret.

**Hoàn tất khi:** test dùng placeholder an toàn; kết luận audit lịch sử được ghi; nếu phát hiện key thật thì đã chuyển giao yêu cầu thu hồi và thống nhất xử lý lịch sử.

### A1 — Đưa Module A vào kiến trúc chung

Di chuyển/refactor theo mapping của review:

| Hiện tại theo review | Đích |
|---|---|
| `src/*` (logic QA) | `modules/qa/` |
| `src/streamlit_app.py` | `views/qa.py` |
| `src/models/document.py` | Dùng `ParsedDocument` và `Page` từ `core/contracts.py` |
| client LLM riêng của A | `core/llm_client.py` |

Giữ các model đặc thù QA như `Answer` và `Citation` trong `modules/qa/`. Cập nhật imports và mọi điểm gọi trong app/tests/docs. Không tự sửa `core/contracts.py`; nếu mapping hiện tại không đủ, tạo đề xuất contract riêng theo quy trình nhóm.

**Hoàn tất khi:** không còn đường chạy QA độc lập dựa vào `src/`; app chung gọi được trang QA; các kiểu document tương thích với contract dùng chung.

### A2 — Làm cho test chạy từ repo root

1. Cập nhật imports/configuration sau khi chuyển module để pytest tìm package theo cấu trúc chuẩn.
2. Không dựa vào biến môi trường `PYTHONPATH` để làm test pass.
3. Chạy `pytest` từ thư mục gốc repo sau khi A1 hoàn tất; xử lý cả lỗi collection lẫn test failures.
4. Phân biệt lỗi do thay đổi Module A với lỗi nền có sẵn ở module khác và ghi nhận rõ; tiêu chí review cuối cùng vẫn là bộ test toàn repo pass trước khi push.

**Hoàn tất khi:** lệnh `pytest` ở repo root thu thập và chạy được toàn bộ suite mà không cần `PYTHONPATH`, và pass.

### A3 — Dọn dependency và phạm vi PR

1. Tìm nơi dùng `google-generativeai`; nếu không còn import/runtime use, bỏ dependency SDK cũ và giữ `google-genai`.
2. Đổi `specs/001-document-qna-api` sang số spec chưa dùng tiếp theo (review gợi ý `005-document-qna`); kiểm tra mọi tham chiếu đường dẫn trước khi đổi.
3. Đưa sáu file `.specify/scripts/python/*` ra khỏi thay đổi Module A. Nếu chúng đã được commit trong nhánh, xác định cách loại khỏi PR mà không xóa công cụ dùng chung khỏi repo.
4. Cập nhật tài liệu và đường dẫn bị ảnh hưởng.

**Hoàn tất khi:** dependency không còn trùng SDK; spec ID không xung đột; thay đổi Module A không mang theo các script dùng chung.

### A4 — Xác nhận app tích hợp và bàn giao review

1. Mở app chung bằng `streamlit run app.py` và xác nhận trang QA hiển thị/đi được luồng chính.
2. Chạy toàn bộ `pytest` từ repo root.
3. Rà soát diff, tài liệu, imports và log để chắc không có secret.
4. Cập nhật checklist và gửi nhóm trạng thái/diff để Long review lại theo quy trình nhóm.

**Hoàn tất khi:** app tích hợp mở được, suite toàn repo pass, diff sạch và các kết luận audit được ghi lại.

## Ranh giới với Phase 1–4

Sau khi các blockers review được xử lý, mới chọn task kế tiếp từ `plan-phase-1.md` và phần Phase 2–4 của tài liệu Claude. Trước khi thực hiện từng task:

- Đối chiếu mô tả với code hiện tại; ghi nhận sai khác thay vì làm theo giả định.
- Xác minh thông tin biến động (model khả dụng, giá, giới hạn API) từ tài liệu chính thức tại thời điểm triển khai.
- Chốt ưu tiên với mục tiêu Module A và integration; không tạo benchmark “thật” bằng cách bịa gold answers.
- Mỗi thay đổi cần DoD cụ thể và kiểm thử phù hợp; chỉ đánh dấu hoàn tất khi có bằng chứng.

## Checklist

- [x] A0 — Fixture hiện tại đã được thay; người dùng xác nhận key thật cũ trong `.env` đã được thu hồi và fixture lịch sử là dữ liệu giả. Không cần rewrite lịch sử.
- [x] A1 — Logic QA ở `modules/qa/`, trang tích hợp ở `views/qa.py`, dùng `core.contracts` và `core.llm_client`.
- [x] A2 — `python -m pytest -q` chạy từ repo root, không đặt `PYTHONPATH`.
- [x] A3 — SDK cũ được bỏ, spec được đánh số lại, sáu script Python Specify được loại khỏi nhánh.
- [x] A4 — QA page được nạp qua kiểm thử AppTest; toàn bộ test pass. App Streamlit chung đã khởi động thành công.

## Kết quả thực thi 09/11/2026

- Baseline ban đầu: pytest collection lỗi ở import của Module A và môi trường thiếu dependency `ortools`.
- Sau sửa: `python -m pytest -q` — 91 passed.
- Review lịch sử: Git local có một commit chứa fixture key-like trong test. Không ghi/hiển thị giá trị. Quét snapshot source ở commit đó không thấy khai báo `DEFAULT_GEMINI_API_KEY` hay chuỗi key Google/AQ; `.env` không được track.
- Người dùng xác nhận `.env` từng có key thật, hiện đã để trống và key cũ đã được xóa/thu hồi trong AI Studio; fixture lịch sử dùng chuỗi tuần tự giả. A0 hoàn tất, không cần rewrite lịch sử.
