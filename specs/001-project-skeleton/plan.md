# Implementation Plan: Khung dự án và hợp đồng dữ liệu chung

**Branch**: `001-project-skeleton` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-project-skeleton/spec.md`

## Summary

Dựng một ứng dụng Streamlit nhiều trang (trang chủ + 4 trang module), gói `core/` chứa sáu
dataclass hợp đồng có tự kiểm tra hợp lệ, bộ dữ liệu giả cho mọi cạnh nối, hàm cổng chặn, và
một `llm_client` dùng chung có cache trên đĩa, đếm token và chạy được khi không có khóa API.
Kèm `requirements.txt`, `.env.example`, README cài đặt, mẫu nhật ký AI và bộ `pytest` chạy offline.

## Technical Context

**Language/Version**: Python 3.11+ (thử trên 3.13)

**Primary Dependencies**: streamlit ≥ 1.50 (`st.navigation`, `st.Page`), python-dotenv,
google-genai (nhà cung cấp mặc định, chỉ import khi được gọi); pytest cho kiểm thử

**Storage**: Cache LLM là file JSON trong `.cache/llm/`; đường dẫn SQLite đặt sẵn trong cấu hình
cho module B (B thiết kế bảng)

**Testing**: pytest, kèm `streamlit.testing.v1.AppTest` để kiểm tra từng trang chạy không lỗi

**Target Platform**: Windows/macOS/Linux, chạy cục bộ, mở bằng trình duyệt

**Project Type**: Ứng dụng web một khối (single project), không tách backend

**Performance Goals**: Mở trang < 2 giây; bộ test < 30 giây

**Constraints**: Chạy được không có mạng và không có khóa API; không Docker

**Scale/Scope**: 1 người dùng, 5 trang, 6 hợp đồng dữ liệu, 4 người phát triển song song

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Cách plan tuân thủ | Đạt |
|---|---|---|
| I. AI chỉ đề xuất | `Task.status` mặc định `proposed`; có `source` + `confidence`; hàm `schedulable()` chỉ nhận `confirmed` | ✅ |
| II. Chặn tại cổng | `can_forward(email)` trả `False` với `malicious`; `suspicious` cần `allow_suspicious=True` | ✅ |
| III. Hợp đồng chung | Toàn bộ trong `core/contracts.py`, mock trong `core/mocks.py`, có test | ✅ |
| IV. Đo được | Test offline cho hợp đồng, mock, cache LLM và từng trang | ✅ |
| V. Đơn giản, máy lạ | Streamlit + file cục bộ; thiếu khóa thì `LLMNotConfigured`, trang hiện cảnh báo | ✅ |
| Bảo mật | `.env.example` không chứa bí mật; `.cache/` vào `.gitignore` | ✅ |

Re-check sau Phase 1: vẫn đạt, không có vi phạm cần giải trình.

## Project Structure

### Documentation (this feature)

```text
specs/001-project-skeleton/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── contracts-api.md
│   └── llm-client-api.md
└── tasks.md
```

### Source Code (repository root)

```text
app.py                      # điểm vào: st.navigation tới 5 trang
core/
├── __init__.py
├── config.py               # đọc .env, đường dẫn dữ liệu/cache/db
├── contracts.py            # 6 dataclass + enum + can_forward / schedulable
├── mocks.py                # dữ liệu giả cho từng hợp đồng
└── llm_client.py           # LLMClient: provider, cache, usage
modules/
├── qa/__init__.py          # A — Nam
├── extraction/__init__.py  # B — Trường
├── scheduler/__init__.py   # C — Long
└── email_security/__init__.py  # D — Hoàng Minh
views/                      # mỗi trang Streamlit một file
├── home.py
├── qa.py
├── extraction.py
├── scheduler.py
└── email_security.py
tests/
├── test_contracts.py
├── test_mocks.py
├── test_llm_client.py
└── test_pages.py
ai-log/
├── README.md
└── TEMPLATE.md
data/sample/                # dữ liệu mẫu được commit (không có thông tin cá nhân)
requirements.txt
.env.example
pyproject.toml              # cấu hình pytest
```

**Structure Decision**: Một project duy nhất. Logic nằm trong `core/` và `modules/` (không
import Streamlit) để test được bằng pytest; `views/` chỉ hiển thị. Thư mục trang tên `views/`
thay vì `pages/` để Streamlit không tự sinh menu cũ, vì điều hướng do `st.navigation` quản lý.

## Complexity Tracking

Không có vi phạm constitution.
