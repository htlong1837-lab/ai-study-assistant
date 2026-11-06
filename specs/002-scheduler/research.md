# Research: Lập lịch học

## R1. Rời rạc hoá thời gian

- **Decision**: Ô 30 phút; ô hợp lệ nếu nằm trọn trong khung giờ học của ngày, không giao giờ lên
  lớp, và bắt đầu sau thời điểm hiện tại (`not_before`).
- **Rationale**: Biến bài toán liên tục thành bài toán gán rời rạc mà CP-SAT xử lý tốt;
  30 phút đủ mịn cho lịch học. 35 ngày × 30 ô ≈ 1 000 ô.
- **Alternatives**: Mô hình khoảng thời gian (`IntervalVar`) — biểu diễn gọn hơn nhưng số khối
  mỗi nhiệm vụ phải cố định trước; khó giải thích hơn trong báo cáo.

## R2. Baseline: Earliest Deadline First (EDF)

- **Decision**: Sắp nhiệm vụ theo (hạn nộp tăng, ưu tiên giảm); với mỗi nhiệm vụ, lấy lần lượt các
  ô rảnh sớm nhất còn trống, kết thúc trước hạn, ngày chưa đầy giờ tối đa, đến khi đủ giờ.
- **Rationale**: Trên một máy, không có giờ rảnh xen kẽ và giới hạn giờ/ngày, sắp theo hạn sớm
  nhất tối thiểu hoá độ trễ lớn nhất (quy tắc EDD của Jackson, 1955) — baseline mạnh, dễ giải thích.
  Khi thêm giới hạn giờ/ngày và độ ưu tiên thì không còn đảm bảo tối ưu, nên cần so sánh.
- **Hạn chế dự kiến**: Dồn việc sớm (tải lệch), không cân nhắc ưu tiên khi quá tải, không quay lui.

## R3. Mô hình CP-SAT

Ký hiệu: `T` nhiệm vụ, `S` ô rảnh, `D` ngày; `need_t` = số ô cần (làm tròn lên);
`A_t = {s ∈ S : end(s) ≤ deadline_t}`; `w_t` = 1/2/3 theo ưu tiên thấp/vừa/cao;
`M` = số ô tối đa mỗi ngày.

Biến:
- `x[t,s] ∈ {0,1}` với `s ∈ A_t` — ô `s` dành cho nhiệm vụ `t`.
- `short_t ∈ [0, need_t]` — số ô thiếu.
- `load_d ∈ [0, M]`, `peak` — tải ngày và tải lớn nhất.
- `y[t,s] ∈ {0,1}` — ô `s` mở đầu một khối mới của `t`.

Ràng buộc:
1. Mỗi ô tối đa một nhiệm vụ: `Σ_t x[t,s] ≤ 1`.
2. Đủ giờ hoặc ghi nhận thiếu: `Σ_{s∈A_t} x[t,s] + short_t = need_t`.
3. Giờ tối đa mỗi ngày: `load_d = Σ_{t, s∈d} x[t,s] ≤ M`; `peak = max_d load_d`.
4. Mở khối: `y[t,s] ≥ x[t,s] − x[t,prev(s)]` nếu `prev(s)` là ô liền trước trong cùng ngày,
   ngược lại `y[t,s] ≥ x[t,s]`.

5. Khối tối thiểu `k` ô (mặc định 60 phút): `y[t,s] ⇒ x[t,s+j]` với `j < min(k, need_t)`, các ô
   liền nhau; nếu không đủ ô liền sau thì `y[t,s] = 0`.

Ràng buộc 5 được thêm sau lần chạy thử đầu tiên (2026-11-06, dữ liệu mẫu, 21 ngày): không có nó,
CP-SAT đạt đỉnh tải 1 giờ/ngày nhưng cắt thành 37 khối, phần lớn 30 phút — đúng mục tiêu toán học
nhưng không dùng được thực tế (trọng số tải đỉnh 100 lấn át phạt số khối 1). Thêm ràng buộc:
21 khối, 0 khối < 60 phút, vẫn 1 giờ/ngày; ca 4 tuần × 15 nhiệm vụ còn nhanh hơn (6 s → 3 s) vì
không gian tìm kiếm hẹp lại. EDF không có ràng buộc này, nên bảng chỉ số có cột "Khối < 60 phút".

Mục tiêu (trọng số theo thứ bậc): `min 10 000·Σ w_t·short_t + 100·peak + Σ y[t,s]`.
Thứ tự ưu tiên: đủ giờ cho việc quan trọng ≫ tải đều ≫ ít khối vụn.

- **Rationale**: Ràng buộc "cứng" (không trùng, trước hạn, giờ/ngày) đảm bảo bằng mô hình;
  ràng buộc "mềm" (đủ giờ khi quá tải) thành phạt để luôn có lời giải.
- **Alternatives**: Quy hoạch tuyến tính nguyên với PuLP/CBC (chậm hơn, thêm phụ thuộc);
  thuật toán di truyền (không đảm bảo ràng buộc cứng, khó tái lập).
- **Giới hạn thời gian**: 10 s, 8 luồng; nếu hết giờ trả lời giải `FEASIBLE` tốt nhất.
- **Điều kiện dừng (đo ngày 2026-11-06)**: không có giới hạn sai số, ca 4 tuần × 15 nhiệm vụ luôn
  chạy hết 10 s và chỉ đạt `FEASIBLE`, dù lời giải cách cận dưới chỉ 16 điểm — phần chênh nằm ở số
  khối (do nhiều lời giải đối xứng). Đặt `absolute_gap_limit = 99` (< trọng số tải đỉnh) thì dừng
  sau ~6 s với trạng thái `OPTIMAL`, nghĩa là **thiếu giờ và tải đỉnh đã được chứng minh tối ưu,
  số khối nằm trong 99 so với tối ưu**. Ca 1 tuần × 3 nhiệm vụ: 0,7 s → 0,1 s.

## R4. Chỉ số đánh giá (dùng chung cho cả hai thuật toán)

| Chỉ số | Định nghĩa |
|---|---|
| Kịp hạn | số nhiệm vụ có `short = 0` / tổng nhiệm vụ đã xác nhận |
| Giờ thiếu | `Σ short_t` (giờ), và bản có trọng số `Σ w_t·short_t` |
| Xung đột | số khối trùng giờ lên lớp, trùng nhau, sau hạn hoặc ngoài khung giờ (phải = 0) |
| Đỉnh tải | giờ học lớn nhất trong một ngày |
| Độ lệch tải | độ lệch chuẩn giờ học/ngày trên các ngày từ đầu đến hạn cuối |
| Số khối | số `StudyBlock` (ít hơn = ít chuyển việc) |
| Thời gian chạy | giây |

## R5. Nhắc nhở

- **`.ics`**: viết tay theo RFC 5545 (CRLF, gập dòng 75 byte, escape `,;\`), giờ "floating"
  (giờ địa phương), `VALARM` báo trước. Không thêm thư viện `ics`.
- **Telegram**: `POST https://api.telegram.org/bot<token>/sendMessage` bằng `urllib`.
  Khóa trong `.env`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- **Gửi đúng một lần**: khóa nhắc nhở = `task_id|remind_at|channel`, lưu tập đã gửi; bỏ qua
  nhắc nhở quá hạn hơn 1 giờ (không spam khi máy tắt lâu).
- **Chạy định kỳ**: Streamlit không có tiến trình nền, nên có lệnh
  `python -m modules.scheduler.notify` để Windows Task Scheduler gọi mỗi 5 phút.
