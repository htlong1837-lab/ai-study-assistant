# Implementation Plan: Thí nghiệm so sánh EDF và CP-SAT

**Branch**: `003-scheduler-experiments` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

## Summary

Bộ sinh kịch bản có hạt giống (`experiments/scenarios.py`), script chạy hai thuật toán và ghi kết
quả (`experiments/compare_schedulers.py`), biểu đồ bằng matplotlib. Kết quả ghi vào
`experiments/results/` và được commit để báo cáo trích dẫn.

## Technical Context

- Python 3.11+, dùng lại `modules.scheduler` (không sửa).
- Thêm `matplotlib` vào `requirements.txt`.
- Chạy: `python -m experiments.compare_schedulers [--seeds 10] [--time-limit 10]`.

## Thiết kế kịch bản

Chung: bắt đầu thứ Hai 09/11/2026, 28 ngày, thời khoá biểu mẫu, 7h–22h, tối đa 4 giờ/ngày,
khối tối thiểu 60 phút. Độ ưu tiên chọn ngẫu nhiên đều.

| Kịch bản | Số nhiệm vụ | Số giờ mỗi việc | Hạn nộp (ngày thứ) |
|---|---|---|---|
| Nhẹ | 6 | 2, 3, 4 | 7–27 |
| Vừa | 12 | 2, 3, 4, 6 | 5–27 |
| Quá tải | 18 | 3, 4, 6, 8 | 3–20 |

Tỉ lệ tải = Σ giờ cần / Σ_ngày min(giờ rảnh trong ngày, giờ tối đa/ngày) tính đến hạn cuối.

## Constitution Check

IV (đo được, có baseline) là mục tiêu chính của tính năng; V: chạy offline, không cần khóa. Đạt.

## Structure

```text
experiments/
├── __init__.py
├── scenarios.py           # SCENARIOS, generate(name, seed), load_ratio()
├── compare_schedulers.py  # chạy, ghi runs.csv, summary.md, *.png
└── results/
tests/scheduler/test_scenarios.py
```
