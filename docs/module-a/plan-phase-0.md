# Kế hoạch chi tiết thực thi Phase 0: Khẩn cấp (Bảo mật & Bug thật) - [ĐÃ RÀ SOÁT LỖ HỔNG LOGIC]

> **Mục tiêu**: Loại bỏ triệt để rủi ro rò rỉ API key, chuyển sang mô hình "người dùng tự nhập key theo phiên" có hỗ trợ Default Key của host, loại bỏ hoàn toàn các side effect ghi đĩa ngầm, sửa lỗi định danh (ID collision), chuẩn hóa cascade model thực tế, ngăn ngừa nhiễm độc cache từ fallback và gắn nhãn minh bạch cho mọi câu trả lời.

---

## 1. Kết quả quét & khắc phục các lỗ hổng logic tiềm ẩn (Logic Gaps Review)

Sau khi đối chiếu toàn diện giữa yêu cầu nghiệp vụ, mã nguồn thực tế và tương tác đa tầng (UI - Service - Client - Cache), chúng tôi phát hiện và đã bổ sung giải pháp cho **7 lỗ hổng logic quan trọng**:

| STT | Lỗ hổng logic phát hiện | Rủi ro nếu không xử lý | Giải pháp trong bản kế hoạch mới |
|---|---|---|---|
| **L1** | **Xung đột kiến trúc về Default Key**: Quy tắc cấm `src/` đọc `os.getenv` mâu thuẫn với yêu cầu cho phép người dùng để trống ô key để dùng default key. | Nếu `LLMClient` tự đọc `os.getenv`, vi phạm nguyên tắc cách ly phiên. Nếu không đọc thì không lấy được default key. | **Phân tách 2 tầng rõ ràng**: Tầng thư viện (`LLMClient`) chỉ nhận `api_key` qua tham số khởi tạo (không đọc trộm env/file). Tầng ứng dụng host/UI (`streamlit_app.py`) chịu trách nhiệm đọc `st.secrets` / `os.getenv` của host nếu ô nhập trống, rồi truyền tường minh xuống `QAService(api_key=...)`. |
| **L2** | **Chữ ký hàm `QAService` chưa đồng bộ**: Code hiện tại gọi `QAService()` không truyền client hay key; `streamlit_app.py` sẽ crash khi `LLMClient` đòi hỏi `api_key`. | Toàn bộ ứng dụng và test hiện tại bị vỡ ngay lập tức khi khởi tạo `QAService()`. | Cập nhật `QAService.__init__(self, llm_client: LLMClient \| None = None, api_key: str \| None = None)`. Nếu chưa có `llm_client`, khởi tạo từ `api_key` được truyền vào. |
| **L3** | **Tạo thư mục cache sớm (Eager `mkdir`)**: `LLMClient.__init__` tạo ngay thư mục `.cache/llm` trên đĩa dù chưa có yêu cầu ghi cache. | Vi phạm tiêu chí Task 0.2: *"khởi tạo LLMClient không tạo ra file/thư mục mới trên đĩa"*. | Chuyển sang cơ chế **Lazy `mkdir`**: Chỉ tạo thư mục cache khi thực sự gọi `_write_cache`. |
| **L4** | **Lệch Unicode khi sinh `question_id`**: Tiếng Việt gõ Telex (NFC) và tổ hợp (NFD) cho chuỗi hash SHA256 khác nhau cho cùng một câu hỏi. | Benchmark và Cache miss oan uổng dù người dùng hỏi cùng một nội dung. | Áp dụng `unicodedata.normalize("NFC", question)` trước khi strip, lowercase và hash SHA256. |
| **L5** | **Nhiễm độc Cache từ Local Fallback**: Code hiện tại (`llm_client.py:335`) tự động ghi đè câu trả lời fallback vào cache. | Các lần hỏi sau của cùng câu hỏi sẽ trả về kết quả fallback kém chất lượng từ cache mà không gọi lại LLM thật! | **Quy tắc bất di bất dịch**: Chỉ ghi cache khi `source == "llm"`. Tuyệt đối không cache kết quả fallback hay lỗi. |
| **L6** | **Cascade model bỏ qua lỗi mạng / timeout**: Code cũ chỉ chuyển sang model kế tiếp khi gặp lỗi `404/not found`, còn gặp Timeout hoặc 503 Service Unavailable lại ném lỗi ngay. | Hệ thống không tận dụng được sức mạnh của Cascade khi mạng chập chờn hoặc Google quá tải. | Mở rộng điều kiện Cascade: Bắt cả `404 Not Found`, `503 Service Unavailable`, và `TimeoutError` để chuyển model kế tiếp trước khi rơi về local fallback. |
| **L7** | **Test hiện tại đang sống nhờ Fallback âm thầm**: `test_qa_service.py` pass vì code cũ âm thầm fallback sang keyword search. | Khi siết chặt kiểm tra key, test cũ sẽ fail mà không rõ nguyên nhân. | Cập nhật test cũ sử dụng `Mock/FakeLLMClient` để kiểm tra đúng hành vi logic nghiệp vụ độc lập với API ngoài. |

---

## 2. Kế hoạch chi tiết từng Task trong Phase 0 (Đã cập nhật hoàn chỉnh)

### [x] Task 0.1: Quản lý API Key linh hoạt, hỗ trợ Default Key & Thêm hướng dẫn người dùng `[VERIFY]` [HOÀN THÀNH]

- **Các file tác động**:
  - `src/llm_client.py` (sửa)
  - `src/qa_service.py` (sửa - cập nhật `__init__`)
  - `src/errors.py` (tạo mới)
  - `src/streamlit_app.py` (sửa)
  - `src/utils/security.py` (tạo mới - chứa `mask_secrets`)
  - `.env` (xóa key lộ, gitignore)
  - `docs/module-a/SECURITY_TODO.md` (tạo mới - hướng dẫn thu hồi key cũ bị lộ)
  - `docs/module-a/verification-log.md` (ghi nhận kết quả audit)
  - `tests/test_no_secrets.py` (tạo mới - regex scan)
  - `tests/unit/test_api_key_lifecycle.py` (tạo mới)

- **Các bước thực hiện cụ thể**:
  1. **Tạo `src/errors.py`**:
     - Định nghĩa cây ngoại lệ chuẩn cho Module A:
       - `ModuleAError(Exception)`
       - `MissingAPIKeyError(ModuleAError)`: Ném khi cả người dùng lẫn host đều không cung cấp key hợp lệ.
       - `InvalidAPIKeyError(ModuleAError)`: Ném khi API trả về 401/403/authentication failure.
       - `QuotaExceededError(ModuleAError)`: Ném khi API hết quota (429/ResourceExhausted).
       - `LLMUnavailableError(ModuleAError)`: Ném khi toàn bộ cascade model đều thất bại.
  2. **Refactor `LLMClient` & `QAService`**:
     - Xóa bỏ hoàn toàn `DEFAULT_GEMINI_API_KEY`.
     - `LLMClient.__init__(self, api_key: str, model: str | None = None, ...)`: Bắt buộc nhận `api_key` dạng chuỗi không rỗng; nếu rỗng/None -> ném `MissingAPIKeyError`. Không đọc `os.getenv` hay file bên trong `src/llm_client.py`.
     - `QAService.__init__(self, llm_client: LLMClient | None = None, api_key: str | None = None)`: Nếu `llm_client` là None, khởi tạo `LLMClient(api_key=api_key)`.
  3. **Tạo `src/utils/security.py`**:
     - Viết hàm `mask_secrets(text: str) -> str`: Che giấu các pattern API key (`AIza...`, `AQ....`, `sk-...`) thành dạng `AIza...****`. Mọi chuỗi lỗi hoặc log phải qua hàm này trước khi xuất ra ngoài.
  4. **Nâng cấp Streamlit UI (`src/streamlit_app.py`)**:
     - **Hướng dẫn thân thiện**: Thêm expander `st.sidebar.expander("❓ API Key là gì? Cách lấy key miễn phí")`:
       - Giải thích ngắn gọn: *"API Key giống như một chìa khóa điện tử giúp ứng dụng kết nối tới mô hình AI của Google để đọc và phân tích tài liệu."*
       - Các bước lấy key miễn phí tại [Google AI Studio](https://aistudio.google.com/): Đăng nhập -> Get API Key -> Create API key -> Dán vào ô.
       - Chú thích: *"Nếu bạn không có hoặc không muốn nhập, bạn hoàn toàn có thể **để trống**, ứng dụng sẽ tự động dùng API key mặc định của hệ thống."*
     - **Ô nhập key tùy chọn**: `st.sidebar.text_input("Gemini API key (tùy chọn)", type="password", help="Để trống nếu muốn dùng key mặc định")`.
     - **Logic phân cấp key**:
       - Nếu ô nhập có giá trị: Ưu tiên dùng key cá nhân của người dùng. Hiển thị badge: *"🟢 Đang sử dụng API Key cá nhân của bạn"*.
       - Nếu để trống: Lấy default key từ `st.secrets` hoặc `os.environ.get("GEMINI_API_KEY")` của server host. Hiển thị badge: *"🔵 Đang sử dụng API Key mặc định của hệ thống"*.
       - Nếu cả 2 đều không có: Hiển thị badge: *"🟡 Chưa có API Key. Vui lòng nhập key để hỏi câu hỏi"*, vô hiệu hóa nút "Ask question". Nút upload và parse PDF vẫn hoạt động bình thường.
     - **Nút "Kiểm tra key"**: Gọi lệnh ping nhanh `count_tokens` (không tốn phí, không tốn quota lớn) để xác nhận key đang chọn (cá nhân hoặc default) có hợp lệ không.
     - **Nút "Xóa key"**: Reset ô nhập về rỗng (tự động quay lại dùng default key nếu có).
  5. **Bảo mật & Quét Secret**:
     - Xóa sạch key trong `.env`.
     - Tạo `docs/module-a/SECURITY_TODO.md` ghi nhận key cũ `AQ.Ab8...` cần được thu hồi trên console.
     - Viết test `tests/test_no_secrets.py`: Quét toàn bộ repo không còn chuỗi secret nào.

- **Tiêu chí hoàn thành (DoD)**:
  - Ô nhập API Key trên UI có thể để trống; khi để trống app vẫn trả lời bình thường bằng default key.
  - UI có khối hướng dẫn chi tiết giải thích API Key là gì và cách lấy key.
  - Khi có nhập key cá nhân, hệ thống ưu tiên sử dụng key cá nhân thay vì default key.
  - `LLMClient(api_key="")` ném `MissingAPIKeyError`.
  - Test quét secret và test vòng đời key xanh 100%.

---

### [x] Task 0.2: Bỏ `_ensure_env_file()` và mọi thao tác ghi file cấu hình ngầm [HOÀN THÀNH]

- **Các file tác động**:
  - `src/llm_client.py`
  - `tests/unit/test_no_side_effects.py` (tạo mới)

- **Các bước thực hiện cụ thể**:
  1. Xóa bỏ hoàn toàn hàm `_ensure_env_file()`, `_env_file_path()`, `_load_api_key()` trong `src/llm_client.py`.
  2. Gỡ bỏ `from dotenv import dotenv_values` khỏi `src/llm_client.py`.
  3. Chuyển `self.cache_dir.mkdir(...)` sang chế độ **Lazy initialization** (chỉ gọi `mkdir` khi ghi cache trong `_write_cache`).
  4. Đảm bảo việc khởi tạo `LLMClient` không tạo bất kỳ file hay thư mục nào trên đĩa.
  5. Viết unit test xác minh: Chạy `LLMClient` trong thư mục tạm `tmp_path`, kiểm tra danh sách file trước và sau khởi tạo, đảm bảo không có file lạ được sinh ra.

- **Tiêu chí hoàn thành (DoD)**:
  - Khởi tạo `LLMClient` không tạo ra bất kỳ file `.env` hay file config ngầm nào trên đĩa.
  - Test `test_no_side_effects.py` pass 100%.

---

### [x] Task 0.3: Sửa `answer_id` không duy nhất `[VERIFY]` [HOÀN THÀNH]

- **Các file tác động**:
  - `src/qa_service.py`
  - `src/models/answer.py`
  - `tests/unit/test_id_generation.py` (tạo mới)
  - `docs/module-a/verification-log.md` (cập nhật)

- **Các bước thực hiện cụ thể**:
  1. **Ghi nhận `[VERIFY]`**: Ghi nhận `answer_id=f"answer-{document.doc_id}-{len(document.pages)}"` gây trùng ID khi hỏi nhiều câu trên 1 tài liệu.
  2. **Viết test tái hiện bug trước**: Gọi 2 câu hỏi khác nhau -> assert `answer_id` khác nhau.
  3. **Sửa logic sinh ID**:
     - `answer_id`: `f"answer-{document.doc_id}-{uuid4().hex[:12]}"` (đảm bảo tính duy nhất cho mỗi câu trả lời).
     - `question_id`: Chuẩn hóa Unicode NFC trước khi hash:
       ```python
       import hashlib, unicodedata
       normalized = " ".join(unicodedata.normalize("NFC", question.strip().lower()).split())
       question_id = f"q-{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:12]}"
       ```
  4. Cập nhật `Answer.to_dict()` và `Answer.from_dict()` bảo đảm tương thích dữ liệu.

- **Tiêu chí hoàn thành (DoD)**:
  - Test 2 câu hỏi khác nhau trên cùng doc -> 2 `answer_id` khác nhau.
  - Test cùng 1 câu hỏi (dù gõ Unicode tổ hợp hay dựng sẵn) -> `question_id` hoàn toàn giống nhau.

---

### [x] Task 0.4: Danh mục Model đa tầng: Giữ nguyên các Model mạnh nhất & Bổ sung đầy đủ các Model Miễn phí (Free Tier) `[VERIFY]` [HOÀN THÀNH]

- **Các file tác động**:
  - `config/models.yaml` (tạo mới - chứa cấu hình cả model mạnh cao cấp và model miễn phí)
  - `src/config.py` (tạo mới - load cấu hình, hỗ trợ chọn model)
  - `scripts/list_models.py` (tạo mới - công cụ kiểm tra model thực tế trên API key)
  - `src/llm_client.py` (sửa - tích hợp cascade đa tầng thông minh)
  - `src/streamlit_app.py` (sửa - dropdown phân nhóm rõ ràng giữa model mạnh & model miễn phí)
  - `tests/unit/test_model_config.py` (tạo mới)
  - `docs/module-a/verification-log.md` (cập nhật)

- **Các bước thực hiện cụ thể**:
  1. **Ghi nhận `[VERIFY]` & Thiết kế danh mục đa tầng**:
     - **Nhóm 1: Các mô hình mạnh nhất (Flagship / High-Intelligence)**:
       - **`gemini-4-argon`**: Model **Flagship Reasoning** mạnh nhất hiện tại của Google cho các bài toán phân tích tài liệu phức tạp, suy luận sâu và tổng hợp đa nguồn (Context window 1M tokens, hỗ trợ long decode).
       - **`gemini-3.8-flash`**: Model **High-Intelligence Production Flash** cân bằng hoàn hảo giữa trí tuệ cao, tốc độ phản hồi tức thì và chi phí tiết kiệm.
     - **Nhóm 2: Các mô hình miễn phí (Free Tier - Không mất phí, không cần thẻ)**:
       - **`gemini-2.5-flash`**: Model thế hệ mới có gói Free Tier phong phú, rất mạnh mẽ và ổn định cho người dùng phổ thông.
       - **`gemini-2.0-flash`**: Model tốc độ cực nhanh, có sẵn Free Tier với hạn mức RPM/RPD cao.
       - **`gemini-1.5-flash`**: Model cơ bản phổ cập, dự phòng tin cậy cho Free Tier.
  2. **Viết script CLI `scripts/list_models.py`**:
     - Nhận API key qua `--api-key` hoặc nhắc nhập bảo mật bằng `getpass`.
     - Hỗ trợ cả `google.genai` (SDK mới) và `google.generativeai` (SDK cũ).
     - Liệt kê toàn bộ các model khả dụng trên tài khoản người dùng, hiển thị rõ model nào hỗ trợ `generateContent`.
  3. **Tạo `config/models.yaml`**:
     - Cấu hình chuỗi Cascade đa tầng linh hoạt:
       `cascade: ["gemini-4-argon", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]`
     - Bảng giá & phân loại Tier chính thức:
       ```yaml
       models:
         gemini-4-argon:
           name: "Gemini 4 Argon (Flagship Reasoning - Mạnh nhất)"
           tier: "paid"
           input_per_1m: 2.00
           output_per_1m: 10.00
           cached_input_per_1m: 0.10
           pricing_known: true
         gemini-3.8-flash:
           name: "Gemini 3.8 Flash (High-Intelligence & Fast)"
           tier: "paid_or_tier1"
           input_per_1m: 0.15
           output_per_1m: 0.60
           pricing_known: true
         gemini-2.5-flash:
           name: "Gemini 2.5 Flash (Miễn phí / Free Tier - Cân bằng & Mạnh)"
           tier: "free_tier"
           input_per_1m: 0.075
           output_per_1m: 0.30
           pricing_known: true
         gemini-2.0-flash:
           name: "Gemini 2.0 Flash (Miễn phí / Free Tier - Tốc độ cao)"
           tier: "free_tier"
           input_per_1m: 0.075
           output_per_1m: 0.30
           pricing_known: true
         gemini-1.5-flash:
           name: "Gemini 1.5 Flash (Miễn phí / Free Tier - Dự phòng)"
           tier: "free_tier"
           input_per_1m: 0.075
           output_per_1m: 0.30
           pricing_known: true
       ```
  4. **Tạo `src/config.py`**:
     - Đọc cấu hình từ `config/models.yaml`.
     - Cho phép chọn model ưu tiên chính (Primary Model).
     - Hỗ trợ override cascade bằng biến môi trường `LLM_MODEL_CASCADE`.
     - Hàm tính phí `estimate_cost()`: Tính toán chi phí chính xác theo token thực tế.
  5. **Tích hợp chọn Model trên giao diện (`src/streamlit_app.py`)**:
     - Bổ sung ô chọn trên sidebar với phân nhóm rõ ràng:
       ```python
       model_options = [
           "gemini-4-argon (Mạnh nhất - Flagship Reasoning)",
           "gemini-3.8-flash (Mạnh mẽ & Tốc độ cao)",
           "gemini-2.5-flash (Miễn phí / Free Tier - Cân bằng)",
           "gemini-2.0-flash (Miễn phí / Free Tier - Nhanh)",
           "gemini-1.5-flash (Miễn phí / Free Tier - Dự phòng)",
       ]
       ```
     - Chú thích hướng dẫn dưới ô chọn:
       *"💡 Các mô hình đánh dấu **Miễn phí** sử dụng được ngay với key Google AI Studio thông thường. Các mô hình siêu mạnh yêu cầu tài khoản Google có bật trả phí."*
  6. **Nâng cấp Cascade trong `LLMClient`**:
     - Chạy model người dùng chọn làm ưu tiên số 1.
     - Nếu model gặp lỗi 403 (yêu cầu thanh toán / billing required), 404, 503 (quá tải) hoặc Timeout -> tự động chuyển tiếp sang các model tiếp theo trong cascade (đặc biệt là tự động fallback về nhóm Free Tier để đảm bảo câu trả lời luôn được tạo ra thành công mà không bị crash).
     - Nếu toàn bộ cascade thất bại: Ném `LLMUnavailableError`.

- **Tiêu chí hoàn thành (DoD)**:
  - Tích hợp đầy đủ cả model mạnh hàng đầu (`gemini-4-argon`, `gemini-3.8-flash`) và các model miễn phí (`gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash`).
  - Giao diện phân loại rõ ràng mô hình mạnh vs mô hình miễn phí.
  - Cascade thông minh: Khi chọn model trả phí mà key là Free Tier, tự động lùi về model Free Tier để phục vụ người dùng trơn tru.

- **Tiêu chí hoàn thành (DoD)**:
  - Tích hợp thành công các model mạnh mẽ thế hệ mới (`gemini-4-argon`, `gemini-3.8-flash`, `gemini-3.5-flash`).
  - Giao diện cho phép người dùng tùy chọn model AI theo nhu cầu.
  - Cascade tự động chuyển tiếp mượt mà khi gặp lỗi.
  - Script `scripts/list_models.py` chạy kiểm tra trực tiếp danh sách model khả dụng trên API key.
  - Test ném `LLMUnavailableError` khi cascade rỗng hoặc toàn bộ model thất bại.

---

### [x] Task 0.5: Gắn nhãn câu trả lời từ fallback local & Ngăn ngừa nhiễm độc Cache [HOÀN THÀNH]

- **Các file tác động**:
  - `src/models/answer.py` (sửa)
  - `src/llm_client.py` (sửa)
  - `src/qa_service.py` (sửa)
  - `src/streamlit_app.py` (sửa)
  - `tests/unit/test_fallback_labeling.py` (tạo mới)

- **Các bước thực hiện cụ thể**:
  1. **Mở rộng `Answer` dataclass**:
     - Thêm trường `source: Literal["llm", "cache", "local_fallback"] = "llm"`.
     - Thêm trường `model_used: str | None = None`.
     - Cập nhật `Answer.to_dict()` và `Answer.from_dict()` bảo đảm tương thích ngược (nếu thiếu trường thì gán mặc định `"llm"`).
  2. **Cập nhật `LLMClient.generate_answer` & Chặn Cache Nhiễm Độc**:
     - Khi đọc từ cache thành công: Gán `source = "cache"`.
     - Khi gọi LLM thành công: Gán `source = "llm"`, `model_used = candidate_model`. Sau đó mới ghi vào cache.
     - Khi rơi vào `_fallback_answer()`: Gán `source = "local_fallback"`, `model_used = None`. **TUYỆT ĐỐI KHÔNG GHI VÀO CACHE**.
  3. **Cập nhật `QAService`**:
     - Truyền `source` và `model_used` từ kết quả `generate_answer()` vào `Answer`.
  4. **Cập nhật giao diện Streamlit (`src/streamlit_app.py`)**:
     - Khi hiển thị câu trả lời:
       - Nếu `answer.source == "local_fallback"`: Hiển thị banner cảnh báo màu vàng nổi bật: *"⚠️ Đây là kết quả trích xuất từ khóa nội bộ (Fallback), không phải câu trả lời do AI sinh ra. Vui lòng kiểm tra lại kết nối mạng hoặc API key của bạn."*
       - Nếu `answer.source == "cache"`: Hiển thị badge nhỏ *"⚡ Trả lời từ bộ nhớ đệm (Cache)"*.
       - Hiển thị model đã sử dụng nếu có (`st.caption(f"Mô hình AI: {answer.model_used}")`).

- **Tiêu chí hoàn thành (DoD)**:
  - Unit test kiểm tra: fallback kích hoạt -> `answer.source == "local_fallback"` và cache không bị ghi.
  - Unit test kiểm tra: cache hit -> `answer.source == "cache"`.
  - UI hiển thị đúng banner cảnh báo khi gặp kết quả fallback.

---

## 3. Quản lý phiên bản & Git (Xử lý thực tế)

- **Hiện trạng**: Môi trường Windows hiện tại chưa có binary `git` trong PATH và thư mục `c:\Users\AP\ai` chưa phải là git repo.
- **Phương án thực hiện**:
  1. Bạn có muốn tôi hỗ trợ cài đặt Git qua `winget` hoặc sử dụng git để tạo branch `002-module-a-hardening` và commit riêng từng task (`fix(A-0.X): ...`) không?
  2. Trong suốt quá trình thực hiện Phase 0, duy trì nhật ký thay đổi chi tiết tại `docs/module-a/CHANGELOG.md` và `docs/module-a/verification-log.md` ghi nhận từng task (A-0.1 → A-0.5) kèm diff và kết quả test tương đương với từng commit.

---

## 4. Kế hoạch kiểm thử & Chạy xác thực Phase 0

Lệnh chạy kiểm thử chuẩn hóa:
```powershell
$env:PYTHONPATH = "src"
python -m pytest -q tests/
```
Quy tắc kiểm thử cho Phase 0:
1. Cập nhật test cũ `test_qa_service.py` để sử dụng Mock LLM, không để test cũ phụ thuộc vào fallback ngầm.
2. Viết unit test riêng cho từng task: `test_no_secrets.py`, `test_api_key_lifecycle.py`, `test_no_side_effects.py`, `test_id_generation.py`, `test_model_config.py`, `test_fallback_labeling.py`.
3. Đảm bảo 100% test pass trước khi chuyển sang phase tiếp theo.

---

## 5. Quyết định kỹ thuật đã thống nhất

1. **API Key & Default Key**: Tách rõ tầng UI (đọc default key của host nếu người dùng để trống) và tầng thư viện `LLMClient` (nhận key tường minh, không đọc trộm env).
2. **Expander hướng dẫn**: Thêm hướng dẫn trực quan, dễ hiểu ngay trên sidebar Streamlit.
3. **Chống nhiễm độc Cache**: Không bao giờ cache kết quả fallback.
4. **Cascade linh hoạt**: Bắt cả lỗi mạng/timeout để thử model tiếp theo.
5. **Danh mục Model thế hệ mới**: Cập nhật sang các model mạnh mẽ thế hệ mới nhất gồm `gemini-4-argon` (flagship reasoning, 1M context), `gemini-3.8-flash` (production flash tốc độ cao), và `gemini-3.5-flash`. Thêm dropdown trên UI để người dùng tùy chọn model theo nhu cầu.
