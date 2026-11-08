# Implementation Plan: Trích xuất yêu cầu bài tập (Module B)

**Branch**: `004-extraction` | **Date**: 2026-11-08 | **Master Plan**: [PLAN TRIỂN KHAI — Module B](../../docs/module_b/plans/README.md)

## Summary

Module B đóng vai trò cầu nối ngữ nghĩa giữa email/tài liệu bài tập và bộ lập lịch. 
Áp dụng kiến trúc pipeline lai (Hybrid Pipeline): 
`Văn bản thô → LLM trích cụm thời gian thô + cấu trúc → Rule engine chuẩn hoá datetime → So sánh tất định phát hiện mâu thuẫn → Proposed Task`.
LLM không tự ý tính datetime; datetime do rule engine độc lập tạo ra từ mốc neo thời gian (`received_at`). Sinh viên duyệt và chỉnh sửa trên giao diện Streamlit; chỉ khi bấm xác nhận (`confirm()`), task mới chuyển sang `confirmed` để Module C lập lịch.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: Pydantic v2, Streamlit, SQLite3 (chuẩn Python), python-dateutil / regex.  
**Storage**: SQLite (`db/assistant.db`), schema trong `db/schema.sql`, lớp truy xuất `db/repository.py`.  
**Testing**: pytest, offline hoàn toàn, sử dụng `FakeLLMClient` trong `core/llm_client.py` và dữ liệu giả `core/mocks.py`.  
**Constraints**: 
- Logic trong `modules/extraction/` không import Streamlit.
- Không sửa đổi `core/contracts.py`, `core/mocks.py`, `core/llm_client.py`.
- Tuyệt đối không gọi đồng hồ hệ thống `datetime.now()` trong hàm chuẩn hóa thời gian.

## Constitution Check

| Nguyên tắc | Tuân thủ | Đạt |
|---|---|---|
| I. AI chỉ đề xuất | Mọi task tạo ra có `status = proposed`; chỉ hàm `confirm()` do người dùng gọi mới chuyển sang `confirmed` | ✅ |
| II. Chặn tại cổng | Kiểm tra `can_forward()` qua `gate.py`; email `malicious` hoặc `suspicious` chưa duyệt bị từ chối ngay, không gọi LLM | ✅ |
| III. Hợp đồng chung | Tuân thủ dataclass `ClassifiedEmail`, `ParsedDocument`, `Task` trong `core/contracts.py` | ✅ |
| IV. Đo được | Bộ benchmark `eval/run_eval.py` so sánh 3 cấu hình: `regex_only`, `llm_direct`, `hybrid` | ✅ |
| V. Đơn giản, máy lạ | Chạy offline với Fake LLM; không cần Docker hay server riêng | ✅ |

## Project Structure

```text
modules/extraction/
├── schemas.py              # Pydantic schema cho LLM và dữ liệu trích xuất
├── datetime_normalizer.py  # Động cơ luật tất định chuẩn hoá ngày giờ tiếng Việt
├── gate.py                 # Kiểm tra an toàn nguồn dữ liệu (can_forward)
├── prompts.py              # System prompt, few-shot, PROMPT_VERSION
├── extractor.py            # Trích xuất LLM, kiểm tra evidence, phân trang tài liệu
├── confidence.py           # Tính confidence bằng code
├── matcher.py              # Khớp bài tập trùng lặp hoặc dời hạn
├── conflicts.py            # So sánh tất định phát hiện mâu thuẫn và mơ hồ
└── workflow.py             # Máy trạng thái, xử lý email/doc, confirm, cancel

db/
├── schema.sql              # Bảng tasks, sources, details, conflicts, update_proposals, logs
└── repository.py           # Repository SQLite dùng chung

views/
└── extraction.py           # Giao diện Streamlit duyệt bài tập và giải quyết mâu thuẫn

eval/
├── datetime_cases.yaml     # >= 60 ca test thời gian tiếng Việt
├── gold/                   # Dữ liệu vàng (*.example.json)
├── metrics.py              # F1, Datetime Accuracy, Conflict metrics
└── run_eval.py             # Script chạy benchmark 3 cấu hình

tests/extraction/
├── test_repository.py
├── test_datetime_normalizer.py
├── test_extractor.py
├── test_conflicts.py
├── test_workflow.py
├── test_metrics.py
└── test_e2e_flow.py
```

## Dependencies & Phase Order

`00-recon` → `01-db` → `02-normalizer` → `03-extractor` → `04-conflicts` → `05-workflow` → `06-ui` → `07-eval` → `08-demo`.
