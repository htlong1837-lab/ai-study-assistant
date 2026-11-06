# Kết quả thí nghiệm EDF và CP-SAT

Sinh bởi `python -m experiments.compare_schedulers --seeds 10 --time-limit 10` lúc 2026-11-06 14:44, Python 3.13.7, Intel64 Family 6 Model 191 Stepping 2, GenuineIntel.

Cài đặt chung: 28 ngày từ 09/11/2026, thời khoá biểu mẫu (6 buổi/tuần), khung 7h–22h, tối đa 4 giờ/ngày, ô 30 phút, khối tối thiểu 60 phút (chỉ CP-SAT áp dụng). Giá trị: trung bình ± độ lệch chuẩn trên các seed.

## Nhẹ — 6 nhiệm vụ, tỉ lệ tải 0.18 ± 0.02

| Chỉ số | EDF | CP-SAT | CP-SAT thắng / hòa / thua |
|---|---|---|---|
| Nhiệm vụ kịp hạn (%) | 100.00 ± 0.00 | 100.00 ± 0.00 | 0 / 10 / 0 |
| Giờ thiếu | 0.00 ± 0.00 | 0.00 ± 0.00 | 0 / 10 / 0 |
| Giờ thiếu có trọng số | 0.00 ± 0.00 | 0.00 ± 0.00 | 0 / 10 / 0 |
| Giờ thiếu của việc ưu tiên cao | 0.00 ± 0.00 | 0.00 ± 0.00 | 0 / 10 / 0 |
| Đỉnh tải (giờ/ngày) | 4.00 ± 0.00 | 1.00 ± 0.00 | 10 / 0 / 0 |
| Độ lệch tải (giờ) | 1.49 ± 0.08 | 0.45 ± 0.05 | 10 / 0 / 0 |
| Số khối học | 11.20 ± 1.69 | 18.00 ± 2.31 | 0 / 0 / 10 |
| Khối < 60 phút | 2.40 ± 0.84 | 0.00 ± 0.00 | 10 / 0 / 0 |
| Xung đột | 0.00 ± 0.00 | 0.00 ± 0.00 | 0 / 10 / 0 |
| Thời gian chạy (s) | 0.00 ± 0.00 | 1.61 ± 0.25 | 0 / 0 / 10 |

Trạng thái CP-SAT: OPTIMAL.

## Vừa — 12 nhiệm vụ, tỉ lệ tải 0.44 ± 0.06

| Chỉ số | EDF | CP-SAT | CP-SAT thắng / hòa / thua |
|---|---|---|---|
| Nhiệm vụ kịp hạn (%) | 100.00 ± 0.00 | 100.00 ± 0.00 | 0 / 10 / 0 |
| Giờ thiếu | 0.00 ± 0.00 | 0.00 ± 0.00 | 0 / 10 / 0 |
| Giờ thiếu có trọng số | 0.00 ± 0.00 | 0.00 ± 0.00 | 0 / 10 / 0 |
| Giờ thiếu của việc ưu tiên cao | 0.00 ± 0.00 | 0.00 ± 0.00 | 0 / 10 / 0 |
| Đỉnh tải (giờ/ngày) | 4.00 ± 0.00 | 2.15 ± 0.24 | 10 / 0 / 0 |
| Độ lệch tải (giờ) | 1.95 ± 0.04 | 0.69 ± 0.15 | 10 / 0 / 0 |
| Số khối học | 26.30 ± 2.31 | 36.90 ± 8.08 | 0 / 1 / 9 |
| Khối < 60 phút | 4.60 ± 1.26 | 0.00 ± 0.00 | 10 / 0 / 0 |
| Xung đột | 0.00 ± 0.00 | 0.00 ± 0.00 | 0 / 10 / 0 |
| Thời gian chạy (s) | 0.00 ± 0.00 | 5.99 ± 1.61 | 0 / 0 / 10 |

Trạng thái CP-SAT: OPTIMAL.

## Quá tải — 18 nhiệm vụ, tỉ lệ tải 1.12 ± 0.11

| Chỉ số | EDF | CP-SAT | CP-SAT thắng / hòa / thua |
|---|---|---|---|
| Nhiệm vụ kịp hạn (%) | 79.45 ± 9.44 | 72.21 ± 11.40 | 0 / 3 / 7 |
| Giờ thiếu | 13.90 ± 7.55 | 13.95 ± 7.57 | 0 / 9 / 1 |
| Giờ thiếu có trọng số | 24.10 ± 14.59 | 16.50 ± 8.60 | 6 / 3 / 1 |
| Giờ thiếu của việc ưu tiên cao | 2.70 ± 2.31 | 0.65 ± 1.89 | 6 / 4 / 0 |
| Đỉnh tải (giờ/ngày) | 4.00 ± 0.00 | 4.00 ± 0.00 | 0 / 10 / 0 |
| Độ lệch tải (giờ) | 0.56 ± 0.57 | 0.53 ± 0.52 | 4 / 5 / 1 |
| Số khối học | 37.80 ± 2.82 | 45.00 ± 12.65 | 3 / 0 / 7 |
| Khối < 60 phút | 5.80 ± 1.23 | 0.00 ± 0.00 | 10 / 0 / 0 |
| Xung đột | 0.00 ± 0.00 | 0.00 ± 0.00 | 0 / 10 / 0 |
| Thời gian chạy (s) | 0.01 ± 0.00 | 8.53 ± 2.69 | 0 / 0 / 10 |

Trạng thái CP-SAT: FEASIBLE, OPTIMAL.
