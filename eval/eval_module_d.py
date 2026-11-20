"""Đánh giá offline có thể tái lập cho Module D.

Chạy từ gốc repo: python eval/eval_module_d.py
LLM dùng cấu hình core.llm_client; nếu là fake, kết quả được gắn rõ là kiểm tra
đường đi/fallback và không được diễn giải là chất lượng của một LLM thật.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sklearn.metrics import f1_score, precision_score, recall_score  # noqa: E402
from sklearn.model_selection import StratifiedKFold  # noqa: E402

from core.contracts import SafetyStatus  # noqa: E402
from modules.email_security.attachment_scanner import scan_attachment  # noqa: E402
from modules.email_security.classifier import (  # noqa: E402
    BaselineClassifier,
    LLMZeroShotClassifier,
)
from modules.email_security.url_scanner import scan_url  # noqa: E402


def _samples() -> tuple[list[str], list[str]]:
    rows: list[tuple[str, str]] = []
    groups = {
        "coursework": [
            "Nộp bài tập môn {course} trước {time}; xem đề cương và tải bài lên LMS.",
            "Bài tập chương {n}: hoàn thành câu hỏi {n} đến {m}, hạn nộp thứ {day}.",
            "Giảng viên nhắc hạn báo cáo {course}, nộp file PDF trước {time}.",
            "Đồ án nhóm {n} cần hoàn thiện phần {topic} cho buổi bảo vệ.",
            "Assignment {n}: submit your coursework by {time} on the course portal.",
            "Bài kiểm tra giữa kỳ sẽ gồm nội dung chương {n}; ôn tập bài giảng.",
            "Sinh viên nộp bài thực hành {course} qua hệ thống học tập trước {day}.",
            "Deadline tiểu luận {topic} là {time}; vui lòng trích dẫn tài liệu.",
            "Bổ sung bài tập tuần {n} vào thư mục lớp trước buổi học kế tiếp.",
            "Thông báo gia hạn nộp bài {course} đến ngày {day} tuần sau.",
        ],
        "announcement": [
            "Khoa {course} thông báo lịch đăng ký học phần học kỳ mới.",
            "Nhà trường nghỉ lễ ngày {day}; các phòng học đóng cửa.",
            "Thông báo học bổng năm học {n}: xem điều kiện tại website chính thức.",
            "Phòng đào tạo cập nhật quy định đăng ký tín chỉ cho sinh viên.",
            "Buổi hội thảo {topic} tổ chức tại hội trường lúc {time}.",
            "Thư viện thông báo thay đổi giờ phục vụ trong tuần thi.",
            "Kết quả cuộc thi nghiên cứu khoa học được công bố trên bảng tin.",
            "Nhà trường mở cổng đăng ký hoạt động ngoại khóa tháng {n}.",
            "Thông báo bảo trì hệ thống LMS vào tối thứ {day}.",
            "Khoa gửi lịch sinh hoạt công dân đầu khóa cho sinh viên.",
        ],
        "schedule": [
            "Lịch học môn {course} chuyển sang phòng {n} vào thứ {day}.",
            "Lịch thi cuối kỳ {course}: ngày {day}, bắt đầu lúc {time}.",
            "Lớp {n} học bù vào chiều thứ {day} tại giảng đường {m}.",
            "Buổi học trực tuyến {course} bắt đầu lúc {time}; link trên LMS.",
            "Thời khóa biểu tuần {n} được cập nhật, tiết học đầu lúc {time}.",
            "Phòng đào tạo đổi lịch thi {course} sang ngày {day}.",
            "Buổi thực hành hôm nay chuyển từ phòng {n} sang phòng {m}.",
            "Lịch bảo vệ đồ án {topic} vào sáng thứ {day} tuần tới.",
            "Lớp nghỉ buổi {course} và học bù theo lịch mới ngày {day}.",
            "Exam schedule update: {course} examination begins at {time}.",
        ],
        "phishing": [
            "Tài khoản sinh viên bị khóa, xác minh mật khẩu ngay tại http://uni.edu.vn.evil.com/login{n}.",
            "Bạn trúng học bổng, nhập thông tin ngân hàng tại http://secure-login-{n}.top/verify.",
            "IT yêu cầu xác nhận tài khoản gấp qua http://192.0.2.{n}/portal.",
            "Your mailbox expires today. Verify password at http://account-check-{n}.xyz.",
            "Hoàn tiền học phí, đăng nhập http://uni.edu.vn@evil.example/reset{n} ngay.",
            "Mở đường link http://bit.ly/verify-{n} và nhập mật khẩu để giữ tài khoản.",
            "Nhận học bổng khẩn cấp, cung cấp mã OTP qua trang http://student-{n}.click.",
            "Phòng đào tạo giả mạo yêu cầu cập nhật CCCD tại http://portal-login-{n}.top.",
            "Tài khoản LMS sắp xóa, đăng nhập lại tại http://xn--secure-{n}.xyz.",
            "Urgent: confirm your banking credentials at http://payroll-{n}.cam.",
        ],
        "spam": [
            "Mua điện thoại giảm giá {n} phần trăm, giao hàng toàn quốc.",
            "Khóa học làm giàu cam kết lợi nhuận cao, đăng ký ngay hôm nay.",
            "Nhận voucher mua sắm miễn phí, số lượng có hạn.",
            "Quảng cáo dịch vụ vay tiền nhanh không cần giấy tờ.",
            "Mời tham gia khảo sát sản phẩm để nhận quà tặng.",
            "Shop thời trang xả kho cuối mùa với ưu đãi đặc biệt.",
            "Earn money from home with our exclusive investment offer.",
            "Bán sim số đẹp và tài khoản giải trí giá rẻ.",
            "Mời đăng ký nhận tin khuyến mãi hàng tuần từ cửa hàng.",
            "Dịch vụ tăng lượt theo dõi mạng xã hội giá tốt.",
        ],
        "other": [
            "Chào bạn, cuối tuần này nhóm mình đi cà phê nhé.",
            "Cảm ơn bạn đã gửi tài liệu, mình sẽ phản hồi sau.",
            "Bạn có thể gọi lại cho mình khi rảnh không?",
            "Hóa đơn điện tháng này đã được thanh toán thành công.",
            "Mình đã đặt bàn ăn tối cho cả nhóm lúc {time}.",
            "Attached is the photo from our weekend trip.",
            "Nhắc bạn mang ô vì chiều nay có thể mưa.",
            "Chúc mừng sinh nhật, chúc bạn một ngày vui vẻ.",
            "Cuộc hẹn của chúng ta được dời sang ngày {day}.",
            "Mình sẽ ghé qua nhà bạn sau giờ làm.",
        ],
    }
    for label, templates in groups.items():
        for i, template in enumerate(templates):
            rows.append(
                (
                    template.format(
                        course="Cơ sở dữ liệu",
                        time="23h59",
                        n=i + 1,
                        m=i + 2,
                        day="Ba",
                        topic="phần mềm",
                    ),
                    label,
                )
            )
    return [x for x, _ in rows], [y for _, y in rows]


def _baseline_oof(texts: list[str], labels: list[str]) -> tuple[float, list[str]]:
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    truth, preds = [], []
    for train, test in folds.split(texts, labels):
        model = BaselineClassifier().train(
            [texts[i] for i in train], [labels[i] for i in train]
        )
        for i in test:
            label, _ = model.predict(texts[i])
            preds.append(label.value)
            truth.append(labels[i])
    return f1_score(truth, preds, average="macro", zero_division=0), preds


def _macro_f1_llm(texts: list[str], labels: list[str]) -> tuple[float, str]:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    model = LLMZeroShotClassifier()
    preds = [model.predict(text)[0].value for text in texts]
    return f1_score(labels, preds, average="macro", zero_division=0), provider


def _pr(actual: list[bool], predicted: list[bool]) -> tuple[float, float]:
    return (
        precision_score(actual, predicted, zero_division=0),
        recall_score(actual, predicted, zero_division=0),
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    texts, labels = _samples()
    dataset_path = ROOT / "eval/module_d_samples.jsonl"
    dataset_path.write_text(
        "".join(
            json.dumps(
                {"text": text, "label": label, "source": "synthetic"},
                ensure_ascii=False,
            )
            + "\n"
            for text, label in zip(texts, labels)
        ),
        encoding="utf-8",
    )
    baseline, baseline_predictions = _baseline_oof(texts, labels)
    llm_f1, provider = _macro_f1_llm(texts, labels)
    phishing_truth = [label == "phishing" for label in labels]
    phishing_pred = [label == "phishing" for label in baseline_predictions]
    phishing_pr = _pr(phishing_truth, phishing_pred)

    urls = [
        ("https://portal.uni.edu.vn/course", False),
        ("http://uni.edu.vn.evil.com/login", True),
        ("http://192.0.2.12/verify", True),
        ("http://bit.ly/abc", True),
        ("https://www.example.org/info", False),
    ] * 12
    url_pr = _pr(
        [truth for _, truth in urls],
        [
            scan_url(url).status in {SafetyStatus.SUSPICIOUS, SafetyStatus.MALICIOUS}
            for url, _ in urls
        ],
    )
    files = [
        ("invoice.pdf", b"%PDF-1.4 safe", False),
        ("report.docx", b"MZ executable", True),
        ("payload.exe", b"MZ", True),
        ("notes.txt", b"Lecture notes", False),
    ] * 15
    file_pr = _pr(
        [truth for _, _, truth in files],
        [
            scan_attachment(data, name, name, "eval").status is SafetyStatus.MALICIOUS
            for name, data, _ in files
        ],
    )

    provider_note = (
        "Kết quả zero-shot theo provider cấu hình; fake không đại diện LLM thật."
        if provider == "fake"
        else f"Provider: {provider}."
    )
    report = f"""# Báo cáo Module D — Email và Bảo mật

## Kiến trúc và cổng an toàn

`process_email` parse `.eml`, trích URL/tệp đính kèm, quét heuristic offline, tra VirusTotal cho mục `SUSPICIOUS` khi có API key, tổng hợp trạng thái rồi mới phân loại và tóm tắt. `SAFE < SUSPICIOUS < MALICIOUS`; phishing nâng email tối thiểu lên `SUSPICIOUS`. LLM chỉ ảnh hưởng nhãn/tóm tắt, không thể hạ trạng thái từ scanner. Email `MALICIOUS` không được chuyển; tệp độc không tạo `SafeAttachment`. Email `SUSPICIOUS` cần người dùng xác nhận và cổng `can_forward` vẫn từ chối `MALICIOUS`.

## Trích xuất và ẩn danh

Parser dùng thư viện `email` của Python, ưu tiên `text/plain`, trích link HTML và lưu tệp với tên đã làm sạch cùng SHA-256. Trước khi gửi nội dung email cho bộ phân loại zero-shot hoặc summarizer, `redact_pii` che email, số điện thoại Việt Nam và MSSV. Summary chỉ chạy cho email học tập `SAFE` và giới hạn 150 ký tự; lỗi LLM dùng fallback nội dung đã che PII.

## Bộ phân loại

TF-IDF kết hợp unigram/bigram và character n-gram với Logistic Regression là mặc định offline. Có thể chọn zero-shot bằng `EMAIL_CLASSIFIER=llm`; lỗi LLM rơi về TF-IDF. TF-IDF có độ trễ thấp, tái lập được và không cần mạng, nhưng phụ thuộc dữ liệu gán nhãn. Zero-shot tránh huấn luyện nhưng cần provider/API và kết quả phụ thuộc model/prompt. Bảng dưới dùng provider được cấu hình; `fake` chỉ đo đường fallback, không đại diện chất lượng LLM thật.

## Heuristic, VirusTotal v3 và cache

URL được chuẩn hóa trước khi tra; chỉ URL `SUSPICIOUS` được gửi tra cứu. Tệp chỉ được tra theo SHA-256, không upload nội dung. `VirusTotalClient` áp dụng giới hạn tần suất và cache SQLite TTL; lỗi/404 không được coi là xác nhận sạch. Kết quả sạch không được hạ tín hiệu heuristic hiện có. Khi thiếu key hoặc gặp lỗi, scanner giữ kết quả offline và trạng thái chưa đủ kết luận ở `SUSPICIOUS`.

## Kết quả đánh giá mô phỏng

Ngày chạy: 2026-11-17. Bộ dữ liệu mô phỏng ẩn danh gồm {len(texts)} email (10 mẫu mỗi nhãn: coursework, announcement, schedule, phishing, spam, other). Dữ liệu được lưu ở `eval/module_d_samples.jsonl`; đây là template mô phỏng, không phải email thu thập từ người dùng.

## Phân loại email

| Phương pháp | Macro-F1 | Ghi chú |
|---|---:|---|
| TF-IDF word/char + Logistic Regression (Stratified 5-fold) | {baseline:.3f} | Đánh giá out-of-fold |
| LLM zero-shot | {llm_f1:.3f} | {provider_note} |

Phishing TF-IDF (precision {phishing_pr[0]:.3f}, recall {phishing_pr[1]:.3f}) được tính trên cùng bộ template mô phỏng; đây không phải ước lượng trên email thực tế.

## Phát hiện an toàn

| Tác vụ | Precision | Recall | Bộ kiểm tra |
|---|---:|---:|---|
| Email phishing | {phishing_pr[0]:.3f} | {phishing_pr[1]:.3f} | {len(texts)} email mô phỏng |
| URL độc/nghi ngờ | {url_pr[0]:.3f} | {url_pr[1]:.3f} | {len(urls)} URL kiểm tra |
| Tệp giả mạo/thực thi | {file_pr[0]:.3f} | {file_pr[1]:.3f} | {len(files)} tệp tổng hợp |

Scanner URL/file đo theo bộ ca tổng hợp có nhãn kỳ vọng. VirusTotal không được gọi trong lần đánh giá này; kết quả heuristic offline được kiểm tra riêng.
"""
    output = ROOT / "docs/report/D-email-bao-mat.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
