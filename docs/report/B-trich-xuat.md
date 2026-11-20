# SP2 — Phần B: Trích xuất yêu cầu bài tập

*Người phụ trách: Duy (46 giờ). Bản nháp tài liệu đặc tả chức năng và đánh giá phục vụ Báo cáo sản phẩm SP2 (Application Track). Bám sát kế hoạch tổng thể đồ án, hợp đồng dữ liệu trong `core/contracts.py` và nguyên tắc thiết kế chung của hệ thống.*

---

## B.1. Bài toán và Phạm vi chức năng

### B.1.1. Bối cảnh thực tế và Vấn đề của sinh viên

Trong quá trình học tập đại học, sinh viên thường xuyên tiếp nhận thông tin bài tập, đồ án và tiểu luận từ nhiều kênh phân tán:
1. **Email giảng viên/trợ giảng:** Thông báo giao bài, đính chính đề bài, dời hạn nộp (deadline extension), nhắc nhở quy cách nộp.
2. **Tài liệu đề bài (PDF / Word / Slide):** Chứa yêu cầu chi tiết, các giai đoạn nộp bài, tiêu chí đánh giá (rubric) và quy chuẩn định dạng file nộp.

Thực tế dẫn đến các vấn đề điển hình:
- **Bỏ lỡ hoặc ghi sai hạn nộp:** Hạn nộp trong tiếng Việt được diễn đạt rất phong phú ("23h59 thứ 6 tuần sau", "hết ngày 15/11", "trước buổi học kế tiếp"), sinh viên dễ nhầm lẫn khi tự ghi chú vào sổ tay hoặc Google Calendar.
- **Mâu thuẫn giữa thông báo và đề bài:** Giảng viên gửi file PDF đề bài cũ (ghi deadline ngày 10/11), nhưng trong thân email lại thông báo dời đến ngày 17/11. Sinh viên chỉ đọc một trong hai nguồn sẽ bị nhầm hạn nộp hoặc sai định dạng nộp bài (email yêu cầu nộp link GitHub, trong khi file đề yêu cầu nộp file `.zip` lên LMS).
- **Thiếu sót điều kiện nộp và tiêu chí chấm:** Sinh viên thường chỉ nhớ ngày nộp mà quên mất các điều kiện tiên quyết (đặt tên file theo cú pháp `MSSV_HoTen_Baitap1.zip`, nộp báo cáo kèm slide thuyết trình, tiêu chí chấm theo thang điểm 10).
- **Gánh nặng nhập liệu thủ công:** Các ứng dụng to-do list hiện tại (Todoist, Notion) đòi hỏi sinh viên phải tự sao chép, tự gõ từng trường dữ liệu và tự ước lượng số giờ làm bài.

### B.1.2. Vai trò của Module B trong luồng hệ thống

Module B đóng vai trò **cầu nối xử lý ngữ nghĩa (semantic bridge)** giữa khâu thu nhận dữ liệu thô (Module D và A) và khâu lập lịch thực thi (Module C):
- Nhận email học tập đã quét an toàn (`ClassifiedEmail`) từ **Module D**.
- Nhận nội dung văn bản đề bài theo từng trang (`ParsedDocument`) từ **Module A**.
- Trích xuất thông tin có cấu trúc, chuẩn hóa thời gian tiếng Việt, phát hiện mâu thuẫn giữa các nguồn.
- Đưa ra bản **đề xuất nhiệm vụ (Proposed Task)** trực quan trên giao diện để sinh viên xác nhận/chỉnh sửa.
- Lưu trữ vào cơ sở dữ liệu chung và chuyển giao `Task` hợp lệ (`confirmed`) cho **Module C** xếp lịch tự động.

```
[Module D: Email & Bảo mật]       [Module A: Tài liệu & Hỏi đáp]
 (ClassifiedEmail: an toàn)          (ParsedDocument: text theo trang)
             │                                     │
             └─────────────────┬───────────────────┘
                               ▼
            ┌─────────────────────────────────────┐
            │   B · TRÍCH XUẤT YÊU CẦU BÀI TẬP    │
            │  1. Trích xuất có cấu trúc (LLM)    │
            │  2. Chuẩn hoá ngày giờ tiếng Việt   │
            │  3. Phát hiện mâu thuẫn & mơ hồ     │
            │  4. Quản lý trạng thái & CSDL       │
            └──────────────────┬──────────────────┘
                               ▼
            ┌─────────────────────────────────────┐
            │       SINH VIÊN XÁC NHẬN DUYỆT      │
            │   (Xem nguồn, cảnh báo, sửa inline) │
            └──────────────────┬──────────────────┘
                               ▼ (Task: status=confirmed)
            [Module C: Lập lịch học & Nhắc nhở]
```

### B.1.3. Các nguyên tắc thiết kế bất biến (Constitution)

1. **Nguyên tắc I — AI chỉ đề xuất, người dùng quyết định:** Toàn bộ kết quả do AI trích xuất bắt buộc phải mang trạng thái ban đầu là `proposed`. Hệ thống tuyệt đối không tự động đưa thẳng nhiệm vụ vào lịch biểu của sinh viên khi chưa có sự xác nhận (`confirm()`) tường minh từ người dùng.
2. **Nguyên tắc II — Chặn tại cổng:** Module B chỉ xử lý dữ liệu được chuyển giao từ Module D khi trạng thái an toàn là `safe` (thông qua hàm `can_forward()`). Mọi email hoặc tệp đính kèm bị đánh dấu `malicious` hoặc `suspicious` (chưa duyệt) đều bị từ chối ngay lập tức.
3. **Nguyên tắc III — Truy xuất nguồn gốc rõ ràng (Grounding & Provenance):** Mọi trường dữ liệu trích xuất (hạn nộp, tiêu chí chấm, yêu cầu) đều phải gắn liền với nguồn gốc cụ thể (`source`, ví dụ: `"email:msg-2026-11-02"` hoặc `"de_thi_giua_ky.pdf#p3"`), giúp sinh viên kiểm chứng ngay bằng một cú nhấp chuột.
4. **Nguyên tắc IV — Hợp đồng dữ liệu độc lập:** Giao tiếp thông qua các dataclass chuẩn trong `core/contracts.py`, cho phép module B phát triển và kiểm thử độc lập với dữ liệu giả lập (`core/mocks.py`).

---

## B.2. Danh mục chức năng chi tiết của Module B

Dưới đây là bảng tổng hợp các chức năng của Module B cùng mã phân bổ công việc theo kế hoạch 46 giờ:

| Mã chức năng | Tên chức năng | Mô tả tóm tắt | Giờ kế hoạch | Đầu ra chính |
|---|---|---|---|---|
| **FR-B01** | Trích xuất thông tin bài tập có cấu trúc | Sử dụng LLM với Structured Output (Pydantic Schema) để trích xuất đầy đủ các trường thông tin bài tập từ văn bản | 7h | `RawExtractedAssignment` |
| **FR-B02** | Chuẩn hoá ngày giờ tiếng Việt | Động cơ luật (Rule Engine + Regex) phân giải các cụm từ chỉ thời gian tự nhiên trong tiếng Việt thành `datetime` chuẩn | 5h | `NormalizedDeadline` |
| **FR-B03** | Phát hiện mơ hồ và mâu thuẫn | Đối chiếu chéo giữa email thông báo và file tài liệu để phát hiện lệch hạn nộp, mâu thuẫn hình thức nộp hoặc thiếu thông tin | 5h | `ConflictReport`, `AmbiguityFlag` |
| **FR-B04** | Quy trình xác nhận và Quản lý Task | Vòng đời chuyển trạng thái (`proposed` → `confirmed` / `cancelled`), cho phép sinh viên chỉnh sửa inline trước khi chốt | 3h | `Task` (`core/contracts.py`) |
| **FR-B05** | Giao diện duyệt đề xuất (UI Streamlit) | Màn hình tương tác hiển thị thẻ bài tập, cảnh báo mâu thuẫn, xem văn bản gốc và nút bấm phê duyệt | 4h | `views/extraction.py` |
| **FR-B06** | Cơ sở dữ liệu chung (SQLite Storage) | Thiết kế bảng lưu trữ nhiệm vụ, chi tiết bài tập, lịch sử đối chiếu và trạng thái xử lý | 3h | `db/assistant.db` |
| **FR-B07** | Đánh giá, đo số trên 20 bộ dữ liệu thật | Thu thập, ẩn danh 20 bài tập thực tế, đo F1-score, độ chính xác ngày giờ và tỉ lệ bắt mâu thuẫn | 5h | Báo cáo đo lường, benchmark |
| **FR-B08** | Khảo sát nhu cầu sinh viên & Tổng hợp SP1 | Lập Google Form khảo sát ≥ 30 sinh viên về khó khăn khi theo dõi bài tập, viết SP1 | 5h | Báo cáo SP1 |
| **FR-B09** | Khảo sát giải pháp hiện có | Phân tích LMS nhà trường và Todoist, chỉ ra điểm nghẽn và ưu thế của hệ thống | 2h | Mục khảo sát B.7 |
| **FR-B10** | Nhật ký AI & Báo cáo module B, demo | Ghi chép prompt kỹ thuật, kiểm thử, viết báo cáo SP2 và kịch bản demo | 7h | Nhật ký AI-003, demo video |

---

## B.3. Thiết kế kỹ thuật chi tiết từng chức năng

### B.3.1. FR-B01: Thiết kế Schema và Trích xuất có cấu trúc (Structured LLM Extraction)

#### 1. Cấu trúc Schema mở rộng (`AssignmentDetail`)
Để phục vụ việc lập lịch và hướng dẫn sinh viên làm bài tập, schema trích xuất gồm hai tầng: tầng nhiệm vụ cốt lõi (chuyển sang `Task`) và tầng chi tiết học tập (lưu tại Module B phục vụ sinh viên tra cứu):

```python
class AssignmentDetail(BaseModel):
    title: str = Field(description="Tên bài tập hoặc đồ án")
    course: str = Field(description="Tên môn học hoặc mã môn (ví dụ: CS102, CSDL)")
    raw_deadline_text: str = Field(description="Cụm từ chỉ thời gian nguyên văn trong tài liệu")
    submission_format: list[str] = Field(
        default_factory=list, 
        description="Định dạng nộp: .pdf, .zip, link github, bản in..."
    )
    submission_platform: str = Field(
        description="Nơi nộp bài: LMS, Google Classroom, Email, Teams..."
    )
    naming_convention: str | None = Field(
        default=None, 
        description="Quy cách đặt tên file (ví dụ: [MSSV]_[HoTen]_BT1.zip)"
    )
    grading_criteria: list[str] = Field(
        default_factory=list, 
        description="Các tiêu chí chấm điểm, rubric hoặc thang điểm thành phần"
    )
    estimated_hours: float = Field(
        default=4.0, 
        description="Số giờ ước tính hoàn thành do LLM phân tích dựa trên khối lượng yêu cầu"
    )
    priority_suggestion: Priority = Field(
        default=Priority.MEDIUM, 
        description="Độ ưu tiên gợi ý dựa trên trọng số điểm hoặc tính cấp bách"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, 
        description="Độ tự tin tổng thể của mô hình về việc trích xuất"
    )
```

#### 2. Chiến lược Prompting và Kỹ thuật gọi mô hình
- Sử dụng lớp bọc LLM chung `core/llm_client.py` với cấu hình Structured Output (JSON mode hoặc function calling/Pydantic validation).
- **System Prompt chuẩn hóa:** Cung cấp định nghĩa vai trò là trợ lý phân tích học thuật, đưa ra hướng dẫn rõ ràng về việc trích xuất thông tin khách quan, không suy diễn khi thiếu bằng chứng, và luôn trích nguyên văn cụm từ thời gian để bộ luật phía sau chuẩn hóa.
- **Xử lý tài liệu dài:** Nếu tài liệu đính kèm (A) có nhiều trang, chỉ các trang chứa từ khóa bài tập (`bài tập`, `assignment`, `deadline`, `tiêu chí`, `nộp bài`, `thang điểm`) mới được đưa vào context để tiết kiệm chi phí token và giảm hallucination.

---

### B.3.2. FR-B02: Động cơ Chuẩn hoá Ngày giờ Tiếng Việt (Vietnamese Datetime Normalizer)

Đây là một chức năng trọng tâm, kết hợp giữa **mô hình trích xuất** và **động cơ luật tất định (deterministic rule engine)** để đảm bảo ngày giờ vào lịch tuyệt đối chính xác.

#### 1. Phân loại các mẫu diễn đạt thời gian trong thực tế sinh viên Việt Nam

1. **Dạng tuyệt đối rõ ràng:**
   - `"23:59 ngày 15/11/2026"` -> `2026-11-15 23:59:00`
   - `"trước 17h00 ngày 30-10"` -> `2026-10-30 17:00:00`
   - `"hạn chót 12:00 trưa 20/12/2026"` -> `2026-12-20 12:00:00`
2. **Dạng tương đối theo thứ trong tuần:**
   - `"23h59 thứ sáu tuần sau"` -> Tính theo thứ của tuần liền kề tính từ mốc neo.
   - `"trước chủ nhật tuần này"` -> Chủ nhật kết thúc tuần hiện tại tính từ mốc neo.
   - `"thứ 3 tuần tới lúc 8 giờ sáng"` -> 08:00 của thứ ba tuần kế tiếp.
3. **Dạng tương đối theo ngày/giờ:**
   - `"trong vòng 3 ngày tới"` -> `mốc_neo + timedelta(days=3)`
   - `"sau 48 tiếng nữa kể từ khi gửi thông báo"` -> `mốc_neo + timedelta(hours=48)`
   - `"hết ngày mai"` -> `(mốc_neo + 1 ngày)` vào lúc `23:59:59`
4. **Dạng mốc học kỳ / lịch thi:**
   - `"tuần 10 môn CSDL"` -> Dựa vào cấu hình thời khóa biểu để nội suy ra ngày cụ thể.

#### 2. Kỹ thuật Neo thời gian (Temporal Grounding)
Một sai lầm phổ biến của các chatbot tổng quát là lấy thời gian chạy máy chủ (`datetime.now()`) làm mốc neo cho các câu tương đối. Trong môi trường học tập:
- Nếu bài tập được trích xuất từ **Email (Module D)**: Mốc neo bắt buộc phải là thời điểm email được gửi/nhận (`ClassifiedEmail.received_at`).
- Nếu trích xuất từ **Tài liệu PDF độc lập (Module A)**: Nếu trong văn bản có ngày ban hành thì lấy ngày đó, nếu không có mới lấy ngày quét tài liệu.

#### 3. Bộ quy tắc xử lý trường hợp khuyết thiếu (Edge Cases)
- **Khuyết giờ cụ thể:** Nếu đề bài chỉ ghi *"Hạn nộp: ngày 20/11/2026"*, hệ thống mặc định gán thời gian là `23:59:00` của ngày đó (theo thông lệ các trường đại học thường hết hạn vào cuối ngày).
- **Khuyết năm:** Nếu văn bản ghi *"Hạn ngày 15 tháng 12"*, hệ thống suy luận năm từ mốc neo của email, có xử lý bước nhảy sang năm sau nếu tháng hạn nộp nhỏ hơn tháng của email (giao thừa học kỳ 1).
- **Thời gian trong quá khứ:** Nếu thời gian tính toán ra nằm trước mốc neo, cảnh báo cờ đỏ `OUTDATED_DEADLINE` để người dùng xác nhận lại xem đây có phải bài tập của kỳ trước hay không.

---

### B.3.3. FR-B03: Thuật toán Phát hiện Mơ hồ và Mâu thuẫn (Conflict & Ambiguity Detection)

Điểm cốt lõi tạo nên sự khác biệt của hệ thống đồ án so với các công cụ đơn lẻ là khả năng **đối chiếu đa nguồn (Cross-document validation)** giữa thông báo ngắn (email) và tài liệu gốc (PDF đề bài).

```
   [Dữ liệu Email: D]               [Tài liệu PDF: A]
   - Hạn: 23:59 25/11                - Hạn: 17:00 18/11
   - Nộp: Link Github                - Nộp: File zip lên LMS
            │                                │
            └───────────────┬────────────────┘
                            ▼
              ┌───────────────────────────┐
              │ BỘ SO KHỚP & ĐỐI CHIẾU    │
              │ - So sánh Datetime        │
              │ - So sánh Kênh nộp bài    │
              │ - Đánh giá Độ mơ hồ       │
              └─────────────┬─────────────┘
                            ▼
              ┌───────────────────────────┐
              │ BÁO CÁO CẢNH BÁO (ALERTS) │
              │ ⚠️ Lệch hạn nộp (7 ngày)  │
              │ ⚠️ Mâu thuẫn kênh nộp bài │
              │ Gợi ý: Email mới hơn PDF  │
              └───────────────────────────┘
```

#### 1. Các dạng mâu thuẫn chính
1. **Lệch hạn nộp (Deadline Conflict):**
   - Khoảng chênh lệch: $|\text{deadline}_{\text{email}} - \text{deadline}_{\text{pdf}}| > 0$.
   - Nguyên tắc gợi ý thông minh: Email có `received_at` muộn hơn ngày tạo file PDF thường là thông báo gia hạn của giảng viên $\rightarrow$ Hệ thống gợi ý chọn hạn nộp của Email kèm ghi chú *"Giảng viên có thể đã dời deadline qua email lúc [giờ/ngày]"*.
2. **Mâu thuẫn kênh và định dạng nộp (Submission Conflict):**
   - File PDF ghi: Nộp bản in tại văn phòng khoa.
   - Thân email ghi: Do tình hình dịch/thời tiết, nộp qua Google Drive folder.
   - Hệ thống đánh dấu cả hai phương án và đưa ra câu hỏi trắc nghiệm trực quan cho sinh viên chọn khi xác nhận.

#### 2. Phát hiện tính mơ hồ (Ambiguity Detection)
Hệ thống gắn cờ cảnh báo `AMBIGUOUS` khi gặp các tình huống:
- Thông báo nói *"Nộp vào tuần sau"* nhưng không có thứ hay ngày cụ thể.
- Yêu cầu nộp bài nhưng không nêu rõ nộp cho ai, qua đường link nào hay nền tảng nào.
- Tiêu chí chấm điểm ghi chung chung *"Chấm điểm theo chất lượng hoàn thành"* mà không có thang điểm thành phần.
- **Hành vi xử lý:** Không tự ý bịa đặt thông tin; hiển thị ô cảnh báo màu vàng trên giao diện để sinh viên lưu ý đặt câu hỏi cho giảng viên trong buổi học tiếp theo.

---

### B.3.4. FR-B04 & FR-B06: Quy trình Phê duyệt và Cơ sở dữ liệu SQLite chung

#### 1. Vòng đời trạng thái của Task (State Machine)
Bám sát hợp đồng dữ liệu tại `core/contracts.py`:
- `PROPOSED` (Đề xuất): Nhiệm vụ vừa được AI trích xuất xong, chứa đầy đủ độ tin cậy `confidence`, liên kết nguồn `source`, và cảnh báo mâu thuẫn (nếu có).
- `CONFIRMED` (Đã duyệt): Sinh viên đã nhấn nút xác nhận trên giao diện (hoặc đã sửa lại các trường thông tin). Chỉ các task ở trạng thái này mới được hàm `schedulable()` của Module C cho phép đưa vào thuật toán xếp lịch (EDF / CP-SAT).
- `CANCELLED` (Đã hủy): Sinh viên từ chối đề xuất (ví dụ: email là bài tập nhóm mà sinh viên không phụ trách, hoặc bài tập tự chọn không làm).

#### 2. Thiết kế Cơ sở dữ liệu SQLite (`db/assistant.db`)
Module B phụ trách phần việc chung là thiết lập CSDL SQLite của dự án để đảm bảo dữ liệu được lưu bền vững cục bộ:

```sql
-- Bảng lưu trữ Task cốt lõi (theo contract B -> C)
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    course TEXT NOT NULL,
    deadline TEXT NOT NULL,          -- ISO-8601 string
    estimated_hours REAL NOT NULL,
    priority TEXT NOT NULL,          -- 'low', 'medium', 'high'
    source TEXT NOT NULL,            -- e.g. 'email:e-001', 'doc:d-002#p2'
    confidence REAL NOT NULL,
    status TEXT NOT NULL,            -- 'proposed', 'confirmed', 'cancelled'
    created_at TEXT NOT NULL,
    confirmed_at TEXT
);

-- Bảng chi tiết yêu cầu bài tập mở rộng (phục vụ sinh viên tra cứu)
CREATE TABLE IF NOT EXISTS assignment_details (
    task_id TEXT PRIMARY KEY,
    raw_deadline_text TEXT,
    submission_format TEXT,         -- JSON array: [".pdf", ".zip"]
    submission_platform TEXT,
    naming_convention TEXT,
    grading_criteria TEXT,          -- JSON array các tiêu chí
    has_conflicts INTEGER DEFAULT 0,
    conflict_summary TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Bảng lịch sử trích xuất để kiểm tra độ tin cậy và gỡ lỗi
CREATE TABLE IF NOT EXISTS extraction_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,      -- 'email' hoặc 'document'
    source_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    execution_time_ms REAL,
    raw_response TEXT,
    created_at TEXT NOT NULL
);
```

---

### B.3.5. FR-B05: Giao diện Duyệt đề xuất (Streamlit View)

Giao diện của Module B (tại `views/extraction.py`) được thiết kế theo tư duy **lấy con người làm trung tâm (Human-in-the-loop)**:

1. **Bảng chọn nguồn dữ liệu an toàn:**
   - Hiển thị danh sách các email học tập đã vượt qua cổng chặn bảo mật của Module D (`SafetyStatus.SAFE`).
   - Danh sách các tài liệu PDF đã được Module A trích xuất văn bản.
2. **Khu vực Đề xuất nhiệm vụ (Proposed Cards):**
   - Mỗi đề xuất hiển thị dưới dạng Card trực quan gồm: Tiêu đề việc, Môn học, Hạn nộp đã chuẩn hóa (kèm văn bản gốc để đối chiếu).
   - Thanh điểm tin cậy `confidence` trực quan hóa bằng màu sắc (xanh lá nếu $\ge 85\%$, vàng nếu $60\% - 85\%$, cam nếu $< 60\%$).
   - Nhãn nguồn gốc: Bấm vào mở popup xem trích đoạn email hoặc trang PDF gốc.
3. **Khu vực Cảnh báo mâu thuẫn (Conflict Alerts):**
   - Hiển thị cảnh báo nổi bật (warning box) nếu phát hiện sự bất nhất giữa email và đề bài.
   - Cho phép sinh viên bấm chọn nhanh phương án đúng: `[Dùng hạn nộp từ Email]`, `[Dùng hạn nộp từ PDF]`, hoặc `[Tự nhập hạn mới]`.
4. **Form chỉnh sửa nhanh (Inline Edit) & Phê duyệt:**
   - Sinh viên có thể điều chỉnh lại `Số giờ ước tính` (để Module C xếp lịch vừa sức hơn) và `Độ ưu tiên` (Low / Medium / High).
   - Nút hành động chính: **"Xác nhận vào lịch"** (chuyển sang `confirmed`) và **"Từ chối"** (chuyển sang `cancelled`).

---

## B.4. So sánh phương pháp AI và Lý do lựa chọn

| Phương án tiếp cận | Ưu điểm | Nhược điểm | Đánh giá & Quyết định |
|---|---|---|---|
| **Phương án 1: Heuristic & Regex thuần túy** | - Tốc độ tức thì (< 5ms)<br>- Hoàn toàn miễn phí, không tốn token<br>- Không có hiện tượng bịa đặt (hallucination) | - Rất dễ gãy khi giảng viên đổi cách hành văn<br>- Không hiểu ngữ cảnh môn học, không trích được rubric<br>- Không thể phát hiện mâu thuẫn ngữ nghĩa | **Làm bộ lọc phụ:** Dùng làm động cơ chuẩn hóa cụm từ ngày giờ sau khi LLM đã khoanh vùng. |
| **Phương án 2: Fine-tune mô hình nhỏ (PhoBERT-NER)** | - Chạy được offline cục bộ<br>- Nhận diện thực thể tên môn học, thời gian tương đối tốt | - Mất nhiều thời gian gán nhãn hàng nghìn câu<br>- Không trích xuất được cấu trúc JSON phức tạp hay tiêu chí chấm dài<br>- Vượt quá khung thời gian 5 tuần | **Không chọn** (đã cắt khỏi phạm vi đồ án để tập trung hoàn thiện luồng sản phẩm). |
| **Phương án 3: LLM Zero-shot/Few-shot có Structured Output (Đề xuất)** | - Hiểu sâu sắc ngữ cảnh tiếng Việt học đường<br>- Trích xuất đồng thời cả hạn nộp, tiêu chí chấm, điều kiện nộp<br>- So sánh đối chiếu ngữ nghĩa giữa 2 tài liệu cực tốt | - Có độ trễ (1–3 giây)<br>- Tiêu tốn chi phí API token | **CHỌN:** Phù hợp hoàn hảo với kiến trúc đồ án Application Track. Kết hợp với bộ luật regex để đạt độ chính xác 100% về ngày giờ. |

**Chiến lược kết hợp tối ưu (Hybrid Pipeline):**
Hệ thống sử dụng mô hình lai:
$$\text{Văn bản thô} \xrightarrow{\text{LLM Extraction}} \text{Cụm từ thô} + \text{Cấu trúc} \xrightarrow{\text{Rule Normalizer}} \text{Datetime chuẩn} \xrightarrow{\text{Conflict Checker}} \text{Proposed Task}$$

---

## B.5. Kế hoạch Thí nghiệm, Bộ dữ liệu và Đo lường đánh giá

### B.5.1. Bộ dữ liệu đánh giá (20 mẫu thực tế)
Để đáp ứng chỉ số nghiệm thu theo đề bài, Module B xây dựng bộ kiểm thử gồm **20 mẫu văn bản thực tế** thu thập từ thông báo và đề bài thật của sinh viên đại học (đã được ẩn danh thông tin cá nhân):
- **10 bài tập tiêu chuẩn:** Có đầy đủ thông báo qua email kèm file đề PDF thống nhất.
- **4 trường hợp dời hạn / thay đổi yêu cầu:** Giảng viên gửi email gia hạn khác với hạn ghi trong file đề đính kèm.
- **3 trường hợp diễn đạt thời gian phức tạp:** "23h59 thứ sáu tuần sau", "hết tuần 8", "trước 12h trưa chủ nhật".
- **3 trường hợp mơ hồ hoặc thiếu dữ liệu:** Thông báo ngắn qua email thiếu hạn nộp giờ cụ thể, hoặc thiếu tiêu chí chấm.

### B.5.2. Các chỉ số đo lường chính (Evaluation Metrics)

1. **Độ chính xác trích xuất theo từng trường (Field-level F1-score):**
   - Đánh giá khả năng trích xuất đúng: Tên bài tập, Tên môn học, Hạn nộp nguyên văn, Kênh nộp bài, Tiêu chí chấm điểm.
   - Công thức: $F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$ trên từng trường.
2. **Độ chính xác chuẩn hoá ngày giờ (Datetime Accuracy %):**
   - Đo tỉ lệ `Exact Match` giữa `datetime` hệ thống suy luận được so với nhãn chuẩn của người gán nhãn (chính xác đến cấp độ ngày, giờ, phút).
3. **Tỉ lệ phát hiện mâu thuẫn và mơ hồ (Conflict Detection Recall & Precision):**
   - Khả năng hệ thống phát hiện đúng các ca lệch hạn nộp giữa email và file PDF (mục tiêu Recall $\ge 85\%$).
4. **Hiệu năng và Chi phí:**
   - Thời gian xử lý trung bình mỗi văn bản (Latency in seconds).
   - Số token tiêu thụ trung bình và chi phí tính toán ước tính qua `TokenTracker`.

---

## B.6. Khảo sát giải pháp hiện có (LMS trường học, Todoist)

### B.6.1. Hệ thống quản lý học tập của nhà trường (LMS Moodle, Canvas, Blackboard)
- **Cơ chế hoạt động:** Giảng viên tạo một hoạt động bài tập (Assignment Activity) trực tiếp trên giao diện web của LMS, thiết lập ngày mở và hạn nộp qua lịch chọn ngày giờ. Hệ thống tự động khóa nộp bài và nhắc nhở trên dashboard của sinh viên.
- **Điểm hạn chế lớn trong thực tế:**
  - Không giải quyết được các bài tập giảng viên giao qua email hoặc ghi chú trong trang slide cuối cùng của bài giảng.
  - Khi giảng viên chỉ gửi email dời hạn mà chưa kịp cấu hình lại trên hệ thống LMS, sinh viên thường bị nhầm lẫn và lo sợ bị trừ điểm nộp muộn.
  - Không có tính năng phân tích tiêu chí chấm điểm từ file PDF đề bài để hướng dẫn sinh viên, không thể tự xếp lịch học cá nhân vào các khoảng thời gian rảnh.

### B.6.2. Ứng dụng quản lý công việc Todoist
- **Cơ chế hoạt động:** Todoist là ứng dụng quản lý tác vụ hàng đầu với khả năng nhận diện ngôn ngữ tự nhiên thông minh (Natural Language Input). Khi người dùng gõ: *"Bài tập CSDL thứ 6 tuần sau 23h"*, Todoist tự động phân tích và gán deadline vào lịch.
- **Điểm hạn chế lớn:**
  - **Phụ thuộc hoàn toàn vào nhập liệu thủ công:** Sinh viên phải tự đọc email, tự mở file PDF đề bài, tự tóm tắt và tự tay gõ vào Todoist.
  - **Không có khả năng đọc hiểu tài liệu:** Không thể tải file PDF bài tập dài 10 trang để tự trích xuất rubric hay yêu cầu đặt tên file.
  - **Không có cơ chế phát hiện mâu thuẫn** giữa các tài liệu khác nhau.

### B.6.3. Bảng so sánh tổng hợp

| Tiêu chí so sánh | LMS của trường | Todoist | Module B của nhóm |
|---|---|---|---|
| **Nguồn dữ liệu đầu vào** | Giảng viên tạo trực tiếp trên web | Người dùng tự gõ tay | **Tự động đọc từ Email (D) & PDF đề bài (A)** |
| **Trích xuất tiêu chí chấm (Rubric)** | Có (nếu giảng viên nhập form) | Không có | **Có (LLM đọc hiểu từ file đề bài PDF)** |
| **Chuẩn hoá ngày giờ tiếng Việt tự nhiên** | Không (chọn picker lịch) | Tốt (nhập liệu NLP nhanh) | **Chuyên sâu (neo thời gian theo email)** |
| **Phát hiện mâu thuẫn email vs đề bài** | Hoàn toàn không | Hoàn toàn không | **Có (Cảnh báo lệch hạn & lệch kênh nộp)** |
| **Cơ chế kiểm soát an toàn** | Đóng khung trong trường | Không quét file độc | **Chặn mã độc từ cổng D, AI chỉ đề xuất** |
| **Liên kết tự động sang lịch học** | Chỉ hiện deadline trên lịch | Đặt lịch báo thức | **Chuyển Task sang Module C xếp khối học** |

**Kết luận:** Module B không cạnh tranh với vai trò lưu trữ nộp bài của LMS, mà đóng vai trò là **người trợ lý thông minh** thu gom, giải mã mọi thông báo phân tán của giảng viên, biến các văn bản thụ động thành các nhiệm vụ rõ ràng, minh bạch và an toàn trước khi chuyển sang Module C lập kế hoạch.

---

## B.7. Hạn chế và Hướng phát triển

### B.7.1. Hạn chế hiện tại
- **Phụ thuộc chất lượng text từ Module A:** Nếu file đề bài là tài liệu scan mờ hoặc chụp bằng điện thoại mà Module A chưa tích hợp OCR nâng cao, nội dung văn bản trích xuất có thể bị khuyết chữ, dẫn đến kết quả phân tích của LLM giảm độ tin cậy.
- **Giới hạn ngữ cảnh tài liệu cực dài:** Với các đề bài đồ án dài hàng chục trang kèm nhiều phụ lục, việc gửi toàn bộ văn bản vào LLM có thể tốn chi phí token đáng kể. Hiện tại giải pháp lọc trang từ khóa giải quyết được phần lớn nhưng có thể bỏ sót nếu từ khóa không bao quát.
- **Tiếng Việt viết tắt và thuật ngữ đặc thù:** Các từ lóng sinh viên hoặc quy ước riêng của từng trường (ví dụ: "nộp bài vào buổi DAD", "hạn nộp trước tiết 3 ngày thứ 4") đòi hỏi cấu hình thời khóa biểu chi tiết mới phân giải tuyệt đối chính xác.

### B.7.2. Hướng phát triển sau 5 tuần
- **Tự động soạn thảo email hỏi lại giảng viên:** Khi phát hiện mâu thuẫn nghiêm trọng hoặc đề bài quá mơ hồ, hệ thống đề xuất sẵn một bản thảo email lịch sự để sinh viên chỉ cần bấm gửi hỏi lại giảng viên/trợ giảng.
- **Học thói quen làm bài của sinh viên:** Ghi nhận thời gian thực tế sinh viên hoàn thành bài tập so với thời gian LLM ước tính để cá nhân hóa chỉ số `estimated_hours` cho các bài tập tiếp theo.
- **Tích hợp đồng bộ hai chiều với LMS:** Tự động đối chiếu trạng thái nộp bài trên LMS để tự đánh dấu hoàn thành nhiệm vụ và giải phóng lịch học trên Module C.
