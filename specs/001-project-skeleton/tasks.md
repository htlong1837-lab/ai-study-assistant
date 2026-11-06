# Tasks: Khung dự án và hợp đồng dữ liệu chung

**Input**: Design documents from `/specs/001-project-skeleton/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Có — constitution (nguyên tắc IV) yêu cầu test offline cho hợp đồng và logic.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: chạy song song được (khác file, không phụ thuộc)
- **[Story]**: US1 mở ứng dụng, US2 dữ liệu giả, US3 cửa LLM chung

## Phase 1: Setup

- [x] T001 Tạo thư mục `core/`, `modules/{qa,extraction,scheduler,email_security}/`, `views/`, `tests/`, `ai-log/`, `data/sample/`
- [x] T002 [P] Tạo `requirements.txt` (streamlit, python-dotenv, google-genai, pytest) và `pyproject.toml` cấu hình pytest
- [x] T003 [P] Tạo `.env.example` (LLM_PROVIDER, LLM_MODEL, GEMINI_API_KEY, DB_PATH) và thêm `.cache/` vào `.gitignore`

## Phase 2: Foundational

- [x] T004 Viết `core/config.py`: nạp `.env`, hằng đường dẫn ROOT, DATA_DIR, CACHE_DIR, DB_PATH
- [x] T005 [P] Tạo `__init__.py` cho `core/` và 4 module, mỗi module ghi docstring người phụ trách và hợp đồng vào/ra

## Phase 3: User Story 2 — Dữ liệu giả và hợp đồng (P1)

**Goal**: 6 hợp đồng có kiểm tra hợp lệ, có mock, có cổng chặn.
**Independent Test**: `pytest tests/test_contracts.py tests/test_mocks.py`

- [x] T006 [P] [US2] Viết test hợp lệ/không hợp lệ cho từng dataclass và `can_forward`, `schedulable` trong `tests/test_contracts.py`
- [x] T007 [P] [US2] Viết test số lượng và độ phủ trạng thái của mock trong `tests/test_mocks.py`
- [x] T008 [US2] Cài đặt enum, 6 dataclass, `can_forward`, `schedulable`, chuyển trạng thái Task trong `core/contracts.py`
- [x] T009 [US2] Cài đặt `core/mocks.py` với `BASE_TIME` cố định

## Phase 4: User Story 3 — Cửa LLM chung (P2)

**Goal**: `LLMClient` có cache, đếm token, chạy được khi thiếu khóa.
**Independent Test**: `pytest tests/test_llm_client.py`

- [x] T010 [P] [US3] Viết test: thiếu khóa → `LLMNotConfigured`; provider `fake` → cache hit lần 2; cache hỏng → gọi lại; usage đúng trong `tests/test_llm_client.py`
- [x] T011 [US3] Cài đặt `core/llm_client.py` (provider `fake`, `gemini` import lười, cache JSON, usage)

## Phase 5: User Story 1 — Mở ứng dụng (P1)

**Goal**: `streamlit run app.py` mở 5 trang không lỗi, không cần khóa.
**Independent Test**: `pytest tests/test_pages.py` + mở bằng trình duyệt

- [x] T012 [P] [US1] Viết test AppTest cho `app.py` và từng file `views/*.py` trong `tests/test_pages.py`
- [x] T013 [US1] Viết `app.py` với `st.navigation` và nhóm trang
- [x] T014 [P] [US1] Viết `views/home.py`: mô tả luồng, trạng thái LLM, bảng thống kê mock
- [x] T015 [P] [US1] Viết `views/scheduler.py`: bảng task mẫu, đánh dấu task được xếp lịch
- [x] T016 [P] [US1] Viết `views/qa.py`, `views/extraction.py`, `views/email_security.py`: trang giữ chỗ hiển thị mock đầu vào

## Phase 6: Polish

- [x] T017 [P] Tạo `ai-log/README.md` và `ai-log/TEMPLATE.md` theo đúng các trường đề bài mục II
- [x] T018 [P] Cập nhật `README.md`: cài đặt, chạy, cấu trúc thư mục, quy trình spec-kit
- [x] T019 Chạy `pytest` và `streamlit run app.py`, kiểm tra theo `quickstart.md`

## Dependencies

- Setup → Foundational → US2 → US3 → US1 (trang cần hợp đồng, mock và trạng thái LLM).
- Trong mỗi phase: test viết trước, chạy thấy fail, rồi cài đặt.

## Implementation Strategy

MVP = US2 (hợp đồng + mock) vì đó là thứ 3 thành viên khác cần ngay; sau đó US3, US1.
