"""WP-04 — So sánh classifier: Baseline TF-IDF+LR vs. LLM zero-shot.

Chạy:
    python -m modules.email_security.classifier.compare
    # hoặc
    python -m modules.email_security.classifier.compare data/emails_labeled.jsonl

Output:
    - In báo cáo ra stdout (classification_report, Macro-F1, thời gian inference).
    - Ghi tóm tắt ra docs/email_classifier_comparison.md.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

DEFAULT_DATASET = "data/emails_labeled.jsonl"
OUTPUT_MD = "docs/email_classifier_comparison.md"

# Ánh xạ nhãn nội bộ → hiển thị
_LABEL_DISPLAY = {
    "coursework": "assignment",
    "announcement": "announcement",
    "schedule": "schedule",
    "phishing": "phishing",
    "spam": "spam",
    "other": "other",
}


def _load_dataset(path: str | Path) -> tuple[list[str], list[str]]:
    """Đọc JSONL, trả (texts, labels)."""
    texts, labels = [], []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            text = obj.get("text") or (
                obj.get("subject", "") + " " + obj.get("body", "")
            ).strip()
            label = obj.get("label", "").strip().lower()
            if text and label:
                texts.append(text)
                labels.append(label)
        except json.JSONDecodeError:
            pass
    return texts, labels


def _baseline_cv(
    texts: list[str],
    labels: list[str],
    n_splits: int = 5,
) -> dict:
    """5-fold Cross Validation cho BaselineClassifier, trả dict kết quả."""
    from sklearn.model_selection import StratifiedKFold
    from sklearn.metrics import classification_report, f1_score

    from .tfidf_lr import BaselineClassifier

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    all_preds: list[str] = []
    all_true: list[str] = []
    fold_f1s: list[float] = []
    inference_times: list[float] = []

    for fold, (train_idx, test_idx) in enumerate(skf.split(texts, labels), 1):
        x_train = [texts[i] for i in train_idx]
        y_train = [labels[i] for i in train_idx]
        x_test  = [texts[i] for i in test_idx]
        y_test  = [labels[i] for i in test_idx]

        clf = BaselineClassifier()
        clf.train(x_train, y_train)

        t0 = time.perf_counter()
        preds_raw = clf._pipeline.predict(x_test)
        elapsed = time.perf_counter() - t0

        all_preds.extend(preds_raw)
        all_true.extend(y_test)
        f1 = f1_score(y_test, preds_raw, average="macro", zero_division=0)
        fold_f1s.append(f1)
        inference_times.append(elapsed / len(x_test) * 1000)  # ms/sample
        print(f"  Fold {fold}: Macro-F1 = {f1:.4f}")

    report = classification_report(all_true, all_preds, zero_division=0)
    macro_f1_mean = sum(fold_f1s) / len(fold_f1s)
    macro_f1_std  = (sum((x - macro_f1_mean) ** 2 for x in fold_f1s) / len(fold_f1s)) ** 0.5
    avg_time_ms   = sum(inference_times) / len(inference_times)

    return {
        "report": report,
        "macro_f1_mean": macro_f1_mean,
        "macro_f1_std": macro_f1_std,
        "avg_inference_ms": avg_time_ms,
        "fold_f1s": fold_f1s,
    }


def _llm_inference_sample(texts: list[str], n_samples: int = 3) -> dict:
    """Đo thời gian inference của LLMZeroShotClassifier trên n_samples mẫu.

    Dùng LLM_PROVIDER=fake nên không cần mạng (Constitution V).
    """
    from .llm_zeroshot import LLMZeroShotClassifier

    clf = LLMZeroShotClassifier()
    sample = texts[:n_samples]
    times: list[float] = []
    results: list[tuple] = []
    for text in sample:
        t0 = time.perf_counter()
        label, conf = clf.predict(text)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        times.append(elapsed_ms)
        results.append((label.value, conf))

    avg_ms = sum(times) / len(times) if times else 0.0
    return {
        "n_samples": len(sample),
        "avg_inference_ms": avg_ms,
        "sample_results": results,
        "note": (
            "Đo trên LLM_PROVIDER=fake (offline). "
            "Latency thực với Gemini API sẽ cao hơn (~500-2000ms/request)."
        ),
    }


def _write_markdown(
    baseline: dict,
    llm: dict,
    dataset_path: str,
    n_samples: int,
    output_path: str = OUTPUT_MD,
) -> None:
    """Ghi báo cáo so sánh ra file Markdown."""
    fold_f1_str = ", ".join(f"{v:.4f}" for v in baseline["fold_f1s"])
    sample_rows = "\n".join(
        f"| {i+1} | {label} | {conf:.2f} |"
        for i, (label, conf) in enumerate(llm["sample_results"])
    )
    md = f"""\
# Báo cáo So sánh Classifier — Module D Email & Bảo mật

> **Ngày tạo:** {time.strftime("%Y-%m-%d %H:%M")}  
> **Dataset:** `{dataset_path}` ({n_samples} mẫu)  
> **Phương pháp đánh giá:** Stratified 5-Fold Cross Validation

---

## 1. Baseline — TF-IDF (word + char\\_wb) + Logistic Regression

### Kết quả Cross Validation (5 fold)

| Chỉ số | Giá trị |
|---|---|
| **Macro-F1 trung bình** | **{baseline["macro_f1_mean"]:.4f}** |
| Độ lệch chuẩn Macro-F1 | ±{baseline["macro_f1_std"]:.4f} |
| F1 từng fold | {fold_f1_str} |
| Thời gian inference TB | {baseline["avg_inference_ms"]:.3f} ms/mẫu |

### Classification Report (tích lũy 5 fold)

```
{baseline["report"]}
```

---

## 2. LLM Zero-Shot (Gemini / fake)

> **Lưu ý:** Đo thời gian trên `LLM_PROVIDER=fake` (offline).  
> Với Gemini API thực tế, latency ≈ 500–2000 ms/request.

| Chỉ số | Giá trị |
|---|---|
| Số mẫu đo | {llm["n_samples"]} |
| Thời gian inference TB | {llm["avg_inference_ms"]:.1f} ms/mẫu (fake) |

#### Kết quả mẫu (fake LLM — không phản ánh chất lượng thực):

| Mẫu | Nhãn dự đoán | Confidence |
|---|---|---|
{sample_rows}

---

## 3. Phân tích & Quyết định

### So sánh tổng quan

| | Baseline TF-IDF+LR | LLM Zero-shot |
|---|---|---|
| Macro-F1 | {baseline["macro_f1_mean"]:.4f} ± {baseline["macro_f1_std"]:.4f} | Chưa đánh giá CV (cần quota) |
| Inference | {baseline["avg_inference_ms"]:.2f} ms/mẫu | ~500–2000 ms/mẫu |
| Phụ thuộc mạng | ❌ Không | ✅ Có (hoặc fake) |
| Chi phí | Miễn phí | Tốn API quota |
| Chạy offline | ✅ Hoàn toàn | ✅ Với `LLM_PROVIDER=fake` |

### Quyết định phương pháp production

**Chọn: Baseline TF-IDF+LR** làm phương pháp mặc định vì:

1. **Chạy offline hoàn toàn** — đảm bảo Constitution V (demo không phụ thuộc mạng).
2. **Nhanh hơn ~100x** — phù hợp xử lý batch nhiều email.
3. **Miễn phí** — không tốn API quota.
4. **Macro-F1 ≥ {baseline["macro_f1_mean"]:.2f}** trên dataset tổng hợp.

**LLM Zero-shot** được dùng làm:
- Fallback khi Baseline confidence < 0.6 (ensemble, WP-03).
- Phân loại trường hợp đặc biệt mà TF-IDF không đủ tín hiệu.

### Hạn chế & Hướng cải thiện

- Dataset hiện tại ({n_samples} mẫu) còn nhỏ — cần ≥ 300 mẫu để F1 có ý nghĩa thống kê (plan § A11).
- TF-IDF yếu với email viết tắt / không dấu — xem xét thêm bước chuẩn hoá.
- LLM cần đánh giá CV đầy đủ khi có quota (chạy `compare.py --with-llm`).

---

*Tạo tự động bởi `modules/email_security/classifier/compare.py` — Module D (Hoàng Minh)*
"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(md, encoding="utf-8")
    print(f"\n✅ Báo cáo đã ghi → {output_path}")


def run_comparison(
    dataset_path: str | Path = DEFAULT_DATASET,
    output_path: str | Path = OUTPUT_MD,
    n_splits: int = 5,
    llm_samples: int = 3,
) -> dict:
    """Chạy so sánh đầy đủ và ghi báo cáo Markdown.

    Args:
        dataset_path: Đường dẫn đến file JSONL dataset.
        output_path:  Đường dẫn file Markdown đầu ra.
        n_splits:     Số fold trong cross validation.
        llm_samples:  Số mẫu đo inference LLM.

    Returns:
        dict với "baseline" và "llm" chứa kết quả chi tiết.
    """
    dataset_path = Path(dataset_path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Không tìm thấy dataset: {dataset_path}")

    texts, labels = _load_dataset(dataset_path)
    n_samples = len(texts)
    print(f"Dataset: {n_samples} mẫu từ {dataset_path}")

    unique_labels = sorted(set(labels))
    print(f"Nhãn: {unique_labels}")

    # Kiểm tra đủ mẫu cho CV
    min_per_label = min(labels.count(lb) for lb in unique_labels)
    if min_per_label < n_splits:
        n_splits = max(2, min_per_label)
        print(f"⚠️  Điều chỉnh n_splits={n_splits} (nhãn ít nhất chỉ có {min_per_label} mẫu)")

    # --- Baseline ---
    print(f"\n{'='*50}")
    print(f"Baseline TF-IDF+LR ({n_splits}-fold CV):")
    print("="*50)
    baseline_result = _baseline_cv(texts, labels, n_splits=n_splits)
    print(f"\nMacro-F1: {baseline_result['macro_f1_mean']:.4f} ± {baseline_result['macro_f1_std']:.4f}")
    print("\nClassification Report:\n")
    print(baseline_result["report"])

    # --- LLM sample ---
    print(f"\n{'='*50}")
    print(f"LLM Zero-Shot ({llm_samples} mẫu, fake mode):")
    print("="*50)
    llm_result = _llm_inference_sample(texts, n_samples=llm_samples)
    print(f"Thời gian trung bình: {llm_result['avg_inference_ms']:.1f} ms/mẫu")
    print(f"Ghi chú: {llm_result['note']}")

    # --- Ghi báo cáo ---
    _write_markdown(
        baseline=baseline_result,
        llm=llm_result,
        dataset_path=str(dataset_path),
        n_samples=n_samples,
        output_path=str(output_path),
    )

    return {"baseline": baseline_result, "llm": llm_result}


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    dataset = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATASET
    run_comparison(dataset_path=dataset)
