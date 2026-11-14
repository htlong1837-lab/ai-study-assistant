# Sub-Plan 2: Pydantic Schemas & Chuẩn hoá Ngày giờ Tiếng Việt (FR-B01, FR-B02)

> **Mục tiêu:** Định nghĩa các Pydantic schema nội bộ cho LLM extraction và xây dựng động cơ luật tất định phân giải cụm từ thời gian tiếng Việt tự nhiên thành `datetime` chuẩn, có gắn nhãn bằng chứng và giả định.  
> **Ước tính thời gian:** 5 giờ  
> **Phase tương ứng:** Phase 2 (Schemas) & Phase 3 (Datetime Normalizer - TRỌNG TÂM)

---

## 1. Thiết kế Pydantic Schemas (`modules/extraction/schemas.py`)

Nguyên tắc bất biến: **Mọi trường đều nullable**, `null` là giá trị hợp lệ khi văn bản không đề cập. Không ép buộc LLM hallucinate dữ liệu.

```python
class Evidence(BaseModel):
    quote: str = Field(description="Trích nguyên văn cụm từ trong văn bản, không diễn đạt lại")
    location: str = Field(description="'email' hoặc 'p<số trang>'")

class ExField(BaseModel, Generic[T]):
    value: T | None = None
    evidence: Evidence | None = None

class RawDeadline(BaseModel):
    label: str | None = None          # "báo cáo SP1", "nộp slide"...
    raw_text: str                     # Cụm thời gian nguyên văn
    evidence: Evidence

class RawAssignment(BaseModel):
    title: ExField[str]
    course: ExField[str]
    deadlines: list[RawDeadline] = []
    submission_platform: ExField[str]
    submission_format: ExField[list[str]]
    naming_convention: ExField[str]
    grading_criteria: ExField[list[str]]
    estimated_hours: float | None = None
    priority_suggestion: Priority | None = None
    is_extension_notice: bool = False
    refers_to: str | None = None

class ExtractionResult(BaseModel):
    assignments: list[RawAssignment] = []
    not_assignment: bool = False
```

---

## 2. Thiết kế Động cơ Chuẩn hoá Ngày giờ Tiếng Việt (`modules/extraction/datetime_normalizer.py`)

Giao diện hàm thuần (pure function), **tuyệt đối không gọi `datetime.now()`**:

```python
@dataclass
class NormalizedDeadline:
    value: datetime | None           # tz-aware Asia/Ho_Chi_Minh; None nếu không thể phân giải
    anchor: datetime                 # Mốc neo (received_at hoặc ngày tài liệu)
    rule_id: str | None
    assumptions: list[str]           # Các giả định bằng tiếng Việt để hiển thị trên UI
    flags: list[str]                 # 'OUTDATED_DEADLINE', 'AMBIGUOUS', 'UNRESOLVED'
    time_defaulted: bool             # True nếu giờ do hệ thống tự gán 23:59:00

def normalize(text: str, anchor: datetime, semester: SemesterConfig | None = None) -> NormalizedDeadline:
    ...
```

### Bộ quy ước chuẩn hoá bắt buộc:
1. **Tuần:** Bắt đầu thứ Hai, kết thúc Chủ Nhật (ISO 8601).
   - "thứ 6 tuần sau": Thứ Sáu của tuần kế tiếp sau tuần chứa mốc neo.
   - "chủ nhật tuần này": Chủ Nhật của tuần chứa mốc neo.
   - "thứ X" đơn lẻ: Lần xuất hiện gần nhất tiếp theo tính từ mốc neo (kèm cờ `AMBIGUOUS` nếu trùng thứ của mốc neo).
2. **Giờ mặc định:**
   - Nếu không ghi giờ cụ thể $\rightarrow$ Gán `23:59:00`, đặt `time_defaulted = True`, thêm giả định `"Không ghi giờ, giả định 23:59"`.
   - "hết ngày X" $\rightarrow$ `23:59:00`.
   - "12h trưa" $\rightarrow$ `12:00:00`. "12h đêm 15/11" $\rightarrow$ `00:00:00` ngày 16/11 kèm cờ `AMBIGUOUS`.
   - Các buổi: "sáng" (08:00 nếu không có giờ), "chiều" (14:00 nếu không có giờ, hoặc $+12$ nếu có giờ $\le 11$), "tối" (20:00 nếu không có giờ, hoặc $+12$).
3. **Mốc tương đối theo khoảng:**
   - "trong vòng N ngày tới", "sau N tiếng nữa" $\rightarrow$ `anchor + timedelta(...)`.
   - "hết ngày mai" $\rightarrow$ ngày kế tiếp lúc `23:59:00`.
4. **Xử lý năm & thời gian quá khứ:**
   - Thiếu năm: Mặc định năm của mốc neo. Nếu ngày tháng đã trôi qua so với mốc neo:
     - Cách $\le 14$ ngày về quá khứ: Giữ năm hiện tại, gắn cờ `OUTDATED_DEADLINE`.
     - Cách xa hơn về quá khứ (ví dụ email tháng 12 nói "hạn 5/1"): Nhảy sang năm tiếp theo.
   - Khi tính ra `value < anchor`: Luôn gắn cờ `OUTDATED_DEADLINE`.
5. **Mốc học kỳ:**
   - "hết tuần 8", "tuần 10 môn CSDL": Chỉ giải quyết khi có `SemesterConfig(start_date)`. Nếu thiếu cấu hình $\rightarrow$ `value = None`, gắn cờ `UNRESOLVED`.
   - Cụm từ mơ hồ như "buổi học sau", "tuần sau" đứng một mình không có thứ $\rightarrow$ `value = None`, gắn cờ `AMBIGUOUS`, không tự đoán.
6. **Không bao giờ ném Exception:** Mọi input lạ, rác hoặc cú pháp không nhận dạng được đều trả về `value = None`, `rule_id = None`, cờ `UNRESOLVED`.

---

## 3. Nhiệm vụ chi tiết (Checklist)

- [ ] **T02.1 — Cài đặt `modules/extraction/schemas.py`:**
  - Định nghĩa đầy đủ `Evidence`, `ExField`, `RawDeadline`, `RawAssignment`, `ExtractionResult`.
  - Viết unit test kiểm tra serialize/deserialize JSON hợp lệ và chấp nhận mọi trường `None`.
- [ ] **T02.2 — Tạo file cấu hình và test dataset:**
  - `config/semester.example.yaml`: Lưu ngày bắt đầu học kỳ và múi giờ.
  - `eval/datetime_cases.yaml`: Soạn thảo $\ge 60$ ca kiểm thử bao quát toàn bộ các mẫu câu thời gian tiếng Việt thực tế kèm mốc neo và kết quả kỳ vọng.
- [ ] **T02.3 — Cài đặt `modules/extraction/datetime_normalizer.py`:**
  - Module tiền xử lý văn bản: Chuẩn hóa khoảng trắng, chữ thường, chuyển đổi các biến thể (g, h, giờ, :, -, /, .).
  - Parser phân tách (Tokenizing): Nhận diện cụm giờ, cụm ngày, cụm tương đối, cụm tuần học kỳ.
  - Bộ luật kết hợp (Resolution Rules): Ghép các thành phần và neo vào `anchor`.
- [ ] **T02.4 — Kiểm thử đơn vị `tests/extraction/test_datetime_normalizer.py`:**
  - Test tham số hóa (`pytest.mark.parametrize`) đọc toàn bộ các ca từ `eval/datetime_cases.yaml`.
  - Test tính tất định: Cùng input và anchor luôn trả về đúng 1 kết quả, không phụ thuộc giờ máy tính.
  - Test robustness: Chuỗi ký tự rác hoặc câu văn phức tạp không gây crash hệ thống.

---

## 4. Tiêu chí nghiệm thu (Definition of Done)

- 100% test trong `test_datetime_normalizer.py` xanh.
- Không có bất kỳ dòng code nào gọi `datetime.now()` trong `datetime_normalizer.py`.
- Tối thiểu 60 test cases phong phú trong `eval/datetime_cases.yaml`.
