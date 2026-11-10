# Review Module D — Email & Bảo mật

**Phụ trách:** Hoàng Minh  
**Thư mục logic:** `modules/email_security/`  
**Thư mục giao diện:** `views/email_security.py`  
**Ước lượng thời gian:** 45 giờ  
**Cập nhật:** 2026-11-08

---

## Mục lục

1. [Vai trò và vị trí trong hệ thống](#1-vai-trò-và-vị-trí-trong-hệ-thống)
2. [Luồng dữ liệu tổng quan](#2-luồng-dữ-liệu-tổng-quan)
3. [Giao diện dữ liệu (Contracts)](#3-giao-diện-dữ-liệu-contracts)
4. [Danh mục công việc chi tiết (45 giờ)](#4-danh-mục-công-việc-chi-tiết-45-giờ)
5. [Thiết kế kỹ thuật từng chức năng](#5-thiết-kế-kỹ-thuật-từng-chức-năng)
6. [Giao diện Streamlit (Màn hình Hộp thư)](#6-giao-diện-streamlit-màn-hình-hộp-thư)
7. [Rủi ro kỹ thuật & Hướng xử lý](#7-rủi-ro-kỹ-thuật--hướng-xử-lý)
8. [Tiêu chí đánh giá (Constitution Check)](#8-tiêu-chí-đánh-giá-constitution-check)
9. [Checklist hoàn thành](#9-checklist-hoàn-thành)

---

## 1. Vai trò và vị trí trong hệ thống

Module D là **cổng vào duy nhất** của toàn hệ thống. Mọi nội dung từ bên ngoài (email, file đính kèm) **đều phải đi qua D** trước khi đến bất kỳ module nào khác.

```
┌──────────────────────────────────────────────────────────┐
│               NGUYÊN TẮC II – "CHẶN TẠI CỔNG"           │
│                                                          │
│   .eml / file  ──►  [Module D]  ──►  ClassifiedEmail     │
│                       │    │            └──► Module B    │
│                       │    └──►  SafeAttachment          │
│                       │               └──► Module A      │
│                       │                                  │
│                  MALICIOUS  ──►  ❌ CHẶN (không đi tiếp) │
│                  SUSPICIOUS ──►  ⚠️  Hỏi người dùng      │
│                  SAFE       ──►  ✅ Chuyển tiếp          │
└──────────────────────────────────────────────────────────┘
```

**Trách nhiệm cốt lõi:**

| # | Trách nhiệm | Ghi chú |
|---|---|---|
| 1 | Đọc / parse email từ file `.eml` | Gmail API là tuỳ chọn nâng cao |
| 2 | Phân loại email (gán nhãn) | TF-IDF + LR vs. LLM zero-shot, đo Macro-F1 |
| 3 | Tóm tắt email học tập | Chỉ tóm tắt email nhãn ASSIGNMENT / SCHEDULE |
| 4 | Quét an toàn URL | Heuristic trước, VirusTotal khi nghi |
| 5 | Quét file đính kèm | Băm SHA-256 + VirusTotal hash lookup |
| 6 | Quyết định chặn / chuyển tiếp | Áp dụng `can_forward()` từ `core/contracts.py` |
| 7 | Dựng giao diện Streamlit (Inbox) | Nhãn, tóm tắt, cảnh báo an toàn |
| 8 | Đầu việc chung của nhóm | `requirements.txt`, `README`, khảo sát SP1 |

---

## 2. Luồng dữ liệu tổng quan

```
  Người dùng upload .eml
          │
          ▼
  ┌───────────────┐
  │  parse_eml()  │  Đọc header + body + attachments
  └──────┬────────┘
         │
         ├──────────────────────────────────────────┐
         ▼                                          ▼
  ┌──────────────┐                        ┌─────────────────┐
  │  classify()  │                        │  scan_attach()  │
  │  TF-IDF+LR   │                        │  SHA-256 hash   │
  │  LLM fallback│                        │  VirusTotal API │
  └──────┬───────┘                        └────────┬────────┘
         │                                         │
         ▼                                         │
  ┌──────────────┐                                 │
  │ summarize()  │  (chỉ ASSIGNMENT / SCHEDULE)    │
  └──────┬───────┘                                 │
         │                                         │
         ▼                                         ▼
  ┌─────────────────────┐             ┌──────────────────────┐
  │  scan_urls()        │             │  SafeAttachment      │
  │  Heuristic rules    │             │  (path, sha256,      │
  │  VirusTotal fallback│             │   email_id)          │
  └──────┬──────────────┘             └────────────┬─────────┘
         │                                         │
         ▼                                         ▼
  ┌─────────────────────────────┐         ┌────────────────┐
  │       ClassifiedEmail       │         │   Module A     │
  │  (id, sender, subject,      │         │  (Hỏi đáp QA)  │
  │   body, label, safety,      │         └────────────────┘
  │   summary, attachments,     │
  │   label_confidence)         │
  └──────────────┬──────────────┘
                 │
                 ▼
         ┌───────────────┐
         │   Module B    │
         │  (Trích xuất) │
         └───────────────┘
```

---

## 3. Giao diện dữ liệu (Contracts)

Tất cả định nghĩa nằm trong [`core/contracts.py`](../core/contracts.py). Module D **không được tự thêm trường** — mọi thay đổi hợp đồng cần PR riêng và toàn nhóm đồng ý (Constitution, nguyên tắc III).

### 3.1 ClassifiedEmail — Trả về cho Module B

```python
@dataclass
class ClassifiedEmail:
    id: str                        # UUID hoặc message-id từ header email
    sender: str                    # Địa chỉ email người gửi
    subject: str                   # Tiêu đề email
    body: str                      # Nội dung văn bản thuần (đã strip HTML)
    received_at: datetime          # Thời điểm nhận (từ header Date:)
    label: EmailLabel              # Nhãn phân loại (xem bảng enum bên dưới)
    safety: SafetyStatus           # Trạng thái an toàn tổng hợp
    summary: str | None = None     # Tóm tắt LLM (None nếu không phải học tập)
    attachments: list[str] = []    # Danh sách đường dẫn file đính kèm đã lưu
    label_confidence: float = 1.0  # Độ tin cậy phân loại, khoảng [0.0, 1.0]
```

**Enum EmailLabel:**

| Giá trị | Ý nghĩa |
|---|---|
| `ASSIGNMENT` | Email thông báo bài tập, deadline |
| `SCHEDULE` | Lịch học, đổi phòng, nghỉ học |
| `ANNOUNCEMENT` | Thông báo chung từ trường/khoa |
| `SPAM` | Rác, quảng cáo |
| `PHISHING` | Email lừa đảo, giả mạo |
| `OTHER` | Không thuộc các nhóm trên |

**Enum SafetyStatus:**

| Giá trị | Hành động |
|---|---|
| `SAFE` | Chuyển tiếp bình thường |
| `SUSPICIOUS` | Hỏi người dùng trước khi chuyển |
| `MALICIOUS` | **Chặn hoàn toàn**, không đi tiếp |

> **Quy tắc:** `can_forward(email)` trong `core/contracts.py` là bộ lọc cuối cùng. Module D **không được** bypass hàm này khi truyền dữ liệu sang B hoặc A.

### 3.2 SafeAttachment — Chuyển cho Module A

```python
@dataclass
class SafeAttachment:
    path: str       # Đường dẫn file đính kèm đã lưu trên disk (data/sample/...)
    sha256: str     # Mã băm SHA-256, 64 ký tự hex thường (lowercase)
    email_id: str   # ID email cha để truy vết nguồn gốc
```

> **Validation tự động:** `__post_init__` kiểm tra `sha256` đúng định dạng 64 ký tự hex. File có hash trùng với entry malicious trong VirusTotal **không bao giờ** được tạo thành `SafeAttachment`.

---

## 4. Danh mục công việc chi tiết (45 giờ)

| STT | Công việc | Giờ ước tính | Ưu tiên | Phụ thuộc |
|---|---|:---:|:---:|---|
| D1 | Parse email từ file `.eml` | 4 | 🔴 Cao | — |
| D2 | Phân loại email: TF-IDF + Logistic Regression (baseline) | 8 | 🔴 Cao | D1 |
| D3 | Phân loại email: LLM zero-shot (so sánh) | 4 | 🔴 Cao | D1, D2 |
| D4 | Đánh giá Macro-F1, chọn phương pháp sản xuất | 3 | 🔴 Cao | D2, D3 |
| D5 | Tóm tắt email học tập bằng LLM | 4 | 🟡 Trung bình | D2 |
| D6 | Quét an toàn URL (heuristic) | 4 | 🔴 Cao | D1 |
| D7 | Quét URL nâng cao (VirusTotal API) | 3 | 🟡 Trung bình | D6 |
| D8 | Quét file đính kèm: băm SHA-256 | 2 | 🔴 Cao | D1 |
| D9 | Quét file đính kèm: VirusTotal hash lookup | 3 | 🟡 Trung bình | D8 |
| D10 | Giao diện Streamlit: Màn hình Inbox | 5 | 🔴 Cao | D2, D5, D6–D9 |
| D11 | Unit test (pytest, không cần mạng) | 4 | 🔴 Cao | D1–D9 |
| D12 | `requirements.txt` cập nhật + `.env.example` | 1 | 🔴 Cao | — |
| D13 | README hướng dẫn cài đặt / sử dụng Module D | 2 | 🟡 Trung bình | D10 |
| D14 | Khảo sát giải pháp hiện có (SP1) | 2 | 🟡 Trung bình | — |
| **Tổng** | | **49 → gộp buffer 4h → 45h** | | |

> **Ghi chú buffer:** D3 và D7 có thể cắt giảm về prototype nếu trễ tiến độ; D14 có thể làm song song với D1.

---

## 5. Thiết kế kỹ thuật từng chức năng

### 5.1 Parse Email từ file `.eml` (D1 — 4h)

**Công cụ:** `email` (stdlib), `mailparser` hoặc `eml-parser`.

**Đầu ra cần trích xuất:**

```python
{
    "message_id": str,     # Header Message-ID (làm khóa id)
    "sender": str,         # Header From:
    "subject": str,        # Header Subject:
    "date": datetime,      # Header Date: → parse thành datetime
    "body_text": str,      # Phần text/plain (ưu tiên) hoặc strip HTML từ text/html
    "attachments": [       # Danh sách file đính kèm
        {"filename": str, "content": bytes, "mimetype": str}
    ],
    "urls": [str]          # Tất cả URL tìm được trong body và HTML href
}
```

**Lưu file đính kèm:** Vào `data/real/<email_id>/` (đã gitignore), trả về đường dẫn tương đối.

**Fallback khi không có Message-ID:** Sinh UUID v4, ghi log cảnh báo.

---

### 5.2 Phân loại email: TF-IDF + Logistic Regression — Baseline (D2 — 8h)

**Pipeline:**

```
subject + body  →  TfidfVectorizer  →  LogisticRegression  →  EmailLabel
                   (max_features=5000,  (C=1.0, max_iter=1000,
                    ngram_range=(1,2),   multi_class='multinomial')
                    sublinear_tf=True)
```

**Dữ liệu huấn luyện:** Tạo tập nhỏ (~150 email mẫu, ẩn danh hoá) từ các nhãn ASSIGNMENT, SCHEDULE, ANNOUNCEMENT, SPAM, PHISHING, OTHER.

**Lưu model:** `data/models/email_classifier.joblib` (không commit lên git nếu có dữ liệu thật).

**Chạy offline hoàn toàn** — không phụ thuộc API.

**Output:** `(label: EmailLabel, confidence: float)`

> **Áp dụng Constitution nguyên tắc I:** `confidence` luôn được trả về và lưu vào `label_confidence` để người dùng thấy độ chắc chắn.

---

### 5.3 Phân loại email: LLM Zero-shot — So sánh (D3 — 4h)

**Prompt mẫu (gửi qua `core/llm_client.py`):**

```
Phân loại email sau vào một trong các nhãn:
assignment | schedule | announcement | spam | phishing | other

Tiêu đề: {subject}
Nội dung (100 từ đầu): {body[:500]}

Trả về JSON: {"label": "<nhãn>", "confidence": <0.0–1.0>, "reason": "<lý do ngắn gọn>"}
```

**Fallback:** Nếu LLM không khả dụng (thiếu `GEMINI_API_KEY`), tự động dùng kết quả TF-IDF+LR.

**Kết hợp:** Nếu LLM confidence < 0.6, dùng TF-IDF+LR làm tie-breaker.

---

### 5.4 Đánh giá Macro-F1 (D4 — 3h)

**Script:** `experiments/compare_classifiers.py` (tương tự `compare_schedulers.py` đã có)

**Tập kiểm tra:** Tách 20% dữ liệu gán nhãn, stratified split.

**Chỉ số chính:** Macro-F1 (tính đều tất cả nhãn, kể cả nhãn ít mẫu như PHISHING).

**Báo cáo:** Confusion matrix + classification report → ghi vào `experiments/results/email_classifier_comparison.md`.

**Quyết định:** Chọn phương pháp có Macro-F1 cao hơn làm mặc định trong production; ghi lý do vào report (phục vụ SP2).

---

### 5.5 Tóm tắt email học tập bằng LLM (D5 — 4h)

**Điều kiện kích hoạt:** Chỉ gọi LLM tóm tắt khi `label in {ASSIGNMENT, SCHEDULE}`.

**Prompt mẫu:**

```
Tóm tắt email học tập sau thành 1–2 câu ngắn gọn bằng tiếng Việt.
Tập trung vào: deadline, môn học, hành động cần làm.

Tiêu đề: {subject}
Nội dung: {body}
```

**Output:** Chuỗi ≤ 150 ký tự, lưu vào `ClassifiedEmail.summary`.

**Fallback (khi tắt LLM):** Lấy 2 câu đầu của `body`, cắt sau 150 ký tự, thêm "…".

**Cache:** Gọi qua `core/llm_client.py` để tận dụng cache có sẵn, tránh gọi lại cùng email.

---

### 5.6 Quét an toàn URL (D6 — 4h, D7 — 3h)

#### Heuristic rules (D6 — offline, chạy trước):

| Rule | Nhãn trả về | Ví dụ |
|---|---|---|
| Domain giả mạo tên trường (`uni-edu-vn.top`) | `MALICIOUS` | `hoc-bong@uni-edu-vn.top` |
| URL rút gọn (`bit.ly`, `tinyurl`, `t.co`…) | `SUSPICIOUS` | `bit.ly/xxxx` |
| Scheme `http://` (không HTTPS) | `SUSPICIOUS` | — |
| IP address thay tên miền | `SUSPICIOUS` | `http://192.168.x.x/...` |
| Domain có nhiều hyphens (`bank-login-secure.com`) | `SUSPICIOUS` | — |
| Domain trường chính thức (whitelist) | `SAFE` | `*.edu.vn` |

**Implementation:** Regex + danh sách trắng tên miền trường trong config.

#### VirusTotal API (D7 — online, chỉ khi heuristic = SUSPICIOUS):

```python
GET https://www.virustotal.com/api/v3/urls/{url_id}
Header: x-apikey: {VIRUSTOTAL_API_KEY}
```

**Quy tắc quyết định:**
- `malicious >= 3` detector → `MALICIOUS`
- `suspicious >= 5` detector → `SUSPICIOUS`  
- Còn lại → `SAFE`

**Rate limit:** VirusTotal free tier = 4 request/phút → xem [Phần 7](#7-rủi-ro-kỹ-thuật--hướng-xử-lý).

---

### 5.7 Quét file đính kèm (D8 — 2h, D9 — 3h)

#### Băm SHA-256 (D8 — offline):

```python
import hashlib

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()  # 64 ký tự lowercase hex
```

#### VirusTotal hash lookup (D9 — online):

```python
GET https://www.virustotal.com/api/v3/files/{sha256}
Header: x-apikey: {VIRUSTOTAL_API_KEY}
```

**Quy tắc:**
- Hash có trong VT và `malicious >= 3` → `MALICIOUS`, **không tạo `SafeAttachment`**, log cảnh báo.
- Hash có trong VT và `suspicious >= 5` → `SUSPICIOUS`, hỏi người dùng.
- Hash không có trong VT (404) → không có thông tin, coi là `SAFE` (nhưng ghi log).
- Lỗi mạng / hết quota → fallback: giữ trạng thái từ heuristic hoặc SUSPICIOUS.

**Tạo `SafeAttachment` chỉ khi** file được xác nhận SAFE hoặc người dùng chấp nhận SUSPICIOUS.

---

## 6. Giao diện Streamlit (Màn hình Hộp thư)

**File:** [`views/email_security.py`](../views/email_security.py)

### Bố cục màn hình

```
┌────────────────────────────────────────────────────────────┐
│  🛡️ Email & bảo mật — Hoàng Minh (D)                      │
│  Vào: file .eml  |  Ra: ClassifiedEmail (B), SafeAttach(A)│
│  [LLM: gemini-2.0-flash ✅]                                │
├────────────────────────────────────────────────────────────┤
│  📂 Tải lên email (.eml)   [Browse files]                  │
├────────────────────────────────────────────────────────────┤
│  📬 Hộp thư                                                │
│                                                            │
│  An toàn  │ Nhãn      │ Người gửi         │ Tiêu đề       │
│  ─────────┼───────────┼───────────────────┼───────────── │
│  🟢 an toàn│ assignment│ gv.ai@uni.edu.vn  │ [AI] Đề bài… │
│  🟢 an toàn│ schedule  │ phongdaotao@uni…  │ Đổi phòng…   │
│  🔴 độc    │ phishing  │ hoc-bong@uni-edu… │ Nhận học bổng│
│  🟡 nghi ngờ│announcement│ clb.tinhoc@gmail│ Tài liệu ôn…│
│                                                            │
│  [Chi tiết email được chọn]                                │
│    📝 Tóm tắt: "Nộp SP1 trước 23h59 thứ Sáu tuần sau."   │
│    📎 File đính kèm: de_bai_ai.pdf [🟢 sha256: 1a2b…]     │
│    🔗 URL tìm thấy: (không có)                             │
│    ➡️ Chuyển tiếp: CÓ / CHẶN                              │
│                                                            │
│  [⚠️ Chú ý: 1 email bị chặn, 1 email cần xác nhận]       │
└────────────────────────────────────────────────────────────┘
```

### Quy tắc UX

| Trạng thái | Icon | Màu hàng | Nút hành động |
|---|---|---|---|
| `SAFE` | 🟢 | Trắng (bình thường) | "Chuyển sang B/A" |
| `SUSPICIOUS` | 🟡 | Vàng nhạt | "Cho phép thủ công" (xác nhận người dùng) |
| `MALICIOUS` | 🔴 | Đỏ nhạt | "Xem chi tiết" (không có nút chuyển tiếp) |

> **Constitution nguyên tắc I:** Với SUSPICIOUS, luôn hỏi người dùng qua `st.warning` + `st.button("Tôi xác nhận muốn chuyển tiếp")` trước khi gọi module khác.

### Dữ liệu mẫu khi demo (không cần API)

Dùng `core.mocks.emails()` và `core.mocks.attachments()` — đã có 4 email mẫu đủ 3 trạng thái an toàn và 5 loại nhãn.

---

## 7. Rủi ro kỹ thuật & Hướng xử lý

### R1 — Hạn mức VirusTotal (Rate Limit)

| Vấn đề | Hậu quả | Hướng xử lý |
|---|---|---|
| Free tier: 4 req/phút, 500 req/ngày | Lỗi 429 khi quét nhiều email cùng lúc | **Heuristic trước, VT chỉ khi SUSPICIOUS** — giảm ~80% lượt gọi. Cache kết quả VT theo hash/URL (SQLite hoặc dict in-memory). Hiển thị cảnh báo rõ ràng khi hết quota thay vì crash. |

```python
# Pseudo-code chiến lược cache + backoff
@lru_cache(maxsize=512)
def virustotal_lookup(hash_or_url: str) -> VTResult:
    ...
    # Nếu 429: trả về VTResult(status=UNKNOWN, reason="Hết quota hôm nay")
```

---

### R2 — Dữ liệu cá nhân trong email

| Vấn đề | Hậu quả | Hướng xử lý |
|---|---|---|
| Email thật chứa tên, MSSV, nội dung riêng tư | Vi phạm privacy khi demo / commit | **Không commit email thật** (`.gitignore` bao phủ `data/real/`). Tập gán nhãn dùng email ẩn danh. Thay tên/email bằng `[REDACTED]` trước khi gọi LLM summarize nếu cần. |

---

### R3 — LLM hallucinate nhãn sai

| Vấn đề | Hậu quả | Hướng xử lý |
|---|---|---|
| LLM trả về nhãn không hợp lệ hoặc JSON lỗi | Pipeline crash | Wrap `json.loads` trong try/except; nếu parse lỗi → fallback TF-IDF+LR. Validate nhãn bằng `EmailLabel(value)` — sẽ raise `ValueError` nếu sai. |

---

### R4 — File đính kèm quá lớn / định dạng lạ

| Vấn đề | Hậu quả | Hướng xử lý |
|---|---|---|
| File `.exe`, `.zip`, `.iso` lớn | Tốn bộ nhớ, nguy hiểm | Giới hạn kích thước upload (mặc định 50 MB). Chặn ngay các MIME type nguy hiểm (`.exe`, `.bat`, `.cmd`, `.js`, `.vbs`) mà không cần gọi VT — đánh dấu MALICIOUS ngay. |

---

### R5 — Không có mạng khi demo

| Vấn đề | Hậu quả | Hướng xử lý |
|---|---|---|
| Giảng viên chấm offline | VirusTotal và LLM không gọi được | **Constitution nguyên tắc V:** Toàn bộ luồng PHẢI chạy được với `LLM_PROVIDER=fake`. Heuristic URL + SHA-256 chạy hoàn toàn offline. Kết quả VT cached từ lần trước. Demo dùng `mocks.emails()`. |

---

### R6 — Encoding email đa ngôn ngữ

| Vấn đề | Hậu quả | Hướng xử lý |
|---|---|---|
| Email tiếng Việt mã hoá quoted-printable, UTF-8, Windows-1258 | Body rỗng hoặc ký tự lỗi | Dùng `email.policy.default` của Python 3.6+. Fallback `chardet` detect encoding. Log cảnh báo nếu decode thất bại. |

---

## 8. Tiêu chí đánh giá (Constitution Check)

| Nguyên tắc | Yêu cầu | Module D đáp ứng như thế nào |
|---|---|---|
| **I — AI đề xuất, người xác nhận** | Nhãn và tóm tắt mang trạng thái proposed + độ tin cậy | `label_confidence` luôn đi kèm; SUSPICIOUS hỏi người dùng |
| **II — Chặn tại cổng** | MALICIOUS không đi tiếp | `can_forward()` enforce tại tầng view và tầng logic |
| **III — Hợp đồng chung** | Chỉ dùng `ClassifiedEmail`, `SafeAttachment` | Mock data sẵn có trong `core/mocks.py` |
| **IV — Đo được, kiểm chứng được** | Macro-F1, unit test không cần mạng | D4 so sánh 2 phương pháp; D11 pytest offline |
| **V — Đơn giản, chạy offline** | Không crash khi thiếu API key | Heuristic + mock = fallback đầy đủ |

**Chỉ số đánh giá chính:**

| Chỉ số | Mục tiêu | Phương pháp đo |
|---|---|---|
| Macro-F1 phân loại email | ≥ 0.80 (TF-IDF+LR) | Tập test 20%, stratified |
| Độ chính xác phát hiện phishing | ≥ 0.90 Precision | Confusion matrix nhãn PHISHING |
| False Positive rate chặn URL | ≤ 10% | Kiểm tra whitelist domain trường |
| Tỷ lệ tóm tắt sai lệch nội dung | ≤ 5% | Đánh giá thủ công 20 email mẫu |

---

## 9. Checklist hoàn thành

### Giai đoạn 1 (tuần 1–2): Hạ tầng + Phân loại

- [ ] D1 — `parse_eml()` trả về đúng các trường, test với email mẫu
- [ ] D2 — TF-IDF+LR huấn luyện được, lưu model, predict nhanh
- [ ] D3 — LLM zero-shot gọi qua `core/llm_client.py`, fallback khi offline
- [ ] D4 — Script so sánh Macro-F1 chạy được, kết quả ghi vào `experiments/results/`
- [ ] D12 — Thêm dependencies mới vào `requirements.txt`, cập nhật `.env.example`

### Giai đoạn 2 (tuần 2–3): Bảo mật + Tóm tắt

- [ ] D5 — `summarize_email()` chỉ chạy cho ASSIGNMENT/SCHEDULE, có fallback
- [ ] D6 — Heuristic URL scanner, 6 rules, unit test offline pass
- [ ] D7 — VirusTotal URL lookup, cache, xử lý 429 gracefully
- [ ] D8 — `sha256_file()` tính đúng hash, không đọc file vào RAM 1 lần
- [ ] D9 — VirusTotal hash lookup, không tạo SafeAttachment khi MALICIOUS

### Giai đoạn 3 (tuần 3–4): Giao diện + Tài liệu

- [ ] D10 — Màn hình Inbox: bảng màu theo safety, expand chi tiết, nút xác nhận
- [ ] D11 — `pytest tests/email_security/` pass không cần mạng và API key
- [ ] D13 — README Module D: cài đặt, cấu hình `.env`, demo offline
- [ ] D14 — Khảo sát giải pháp hiện có: bộ lọc Gmail, Gemini trong Gmail (SP1)

### Giai đoạn 4 (tuần 4–5): Tích hợp + Báo cáo

- [ ] Tích hợp với Module B: `ClassifiedEmail` chạy qua `mocks.emails()` + thật
- [ ] Tích hợp với Module A: `SafeAttachment` được Module A đọc được
- [ ] `can_forward()` enforce đúng ở mọi điểm chuyển dữ liệu
- [ ] Phần Module D trong báo cáo SP2 hoàn chỉnh (kỹ thuật, đánh giá, hướng phát triển)
- [ ] Nhật ký AI `ai-log/AI-xxx-module-d.md` ghi đủ các phiên sử dụng AI

---

## Phụ lục: Dependencies cần thêm cho Module D

```txt
# Hiện có (requirements.txt)
streamlit>=1.50
python-dotenv>=1.0
google-genai>=1.0
pandas>=2.0
pytest>=8.0

# Cần thêm cho Module D
scikit-learn>=1.4      # TF-IDF + Logistic Regression
joblib>=1.3            # Lưu/load model (đi kèm sklearn, khai báo tường minh)
chardet>=5.2           # Detect encoding email
requests>=2.31         # Gọi VirusTotal REST API
eml-parser>=2.0        # Parse file .eml (hoặc dùng stdlib email, không bắt buộc)
```

---

## Phụ lục: Biến môi trường cần thêm vào `.env.example`

```bash
# --- Module D — Email & Bảo mật ---
VIRUSTOTAL_API_KEY=       # Lấy miễn phí tại https://www.virustotal.com/gui/my-apikey
                           # Để trống = chỉ dùng heuristic (vẫn chạy được)

EMAIL_DOMAIN_WHITELIST=uni.edu.vn,hust.edu.vn
                           # Danh sách domain trường tin cậy, ngăn cách bằng dấu phẩy

EMAIL_ATTACH_MAX_MB=50     # Giới hạn kích thước file đính kèm (MB)
```

---

*Tài liệu này được tạo ngày 2026-11-08. Mọi thay đổi hợp đồng dữ liệu phải qua PR riêng và được toàn nhóm đồng ý (Constitution v1.0.0, nguyên tắc III).*
