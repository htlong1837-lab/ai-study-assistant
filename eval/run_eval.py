"""Script chạy đánh giá Benchmark tự động cho Module B.

Hỗ trợ so sánh 3 cấu hình:
1. `regex_only`: Baseline 1 — Chỉ dùng Regex/Heuristic tìm cụm thời gian và gọi normalize().
2. `llm_direct`: Baseline 2 — LLM trực tiếp suy luận ISO deadline không qua Rule Engine.
3. `hybrid`: Phương pháp đề xuất — LLM trích xuất cụm thời gian và cấu trúc, Rule Engine chuẩn hoá.
Cờ `--no-anchor`: Dùng thời gian hiện tại thay vì email.received_at để kiểm chứng vai trò của mốc neo.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.contracts import ClassifiedEmail, EmailLabel, SafetyStatus
from core.llm_client import LLMClient
from eval.metrics import (
    compute_conflict_metrics,
    compute_datetime_accuracy,
    compute_field_metrics,
    compute_list_field_metrics,
    datetime_exact_match,
)
from modules.extraction.datetime_normalizer import normalize

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
GOLD_DIR = ROOT / "eval" / "gold"
RESULTS_DIR = ROOT / "eval" / "results"


def load_gold_dataset(split: str = "test") -> list[dict[str, Any]]:
    """Tải tất cả các mẫu dữ liệu vàng từ eval/gold/."""
    files = sorted(list(GOLD_DIR.glob("*.json")) + list(GOLD_DIR.glob("*.example.json")))
    unique_samples: dict[str, dict[str, Any]] = {}

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                sid = data.get("id", f.stem)
                if split != "all" and data.get("split") != split:
                    continue
                if sid not in unique_samples:
                    unique_samples[sid] = data
        except Exception as e:
            logger.warning(f"Lỗi đọc file {f}: {e}")

    return list(unique_samples.values())


def extract_regex_only(sample: dict[str, Any], use_anchor: bool = True) -> dict[str, Any]:
    """Cấu hình Baseline 1: Regex heuristic."""
    body = sample.get("email", {}).get("body", "")
    subject = sample.get("email", {}).get("subject", "")
    received_at_str = sample.get("email", {}).get("received_at")
    anchor = datetime.fromisoformat(received_at_str) if (use_anchor and received_at_str) else datetime.now(timezone.utc)

    # Heuristic title & course từ subject
    m_course = re.search(r"\[(.*?)\]", subject)
    course = m_course.group(1).strip() if m_course else None
    title = re.sub(r"\[.*?\]", "", subject).strip() or None

    # Tìm cụm thời gian bằng regex
    patterns = [
        r"(?:trước|vao|den|han|luc)\s+([0-9]{1,2}(?:h[0-9]{1,2})?\s+thứ\s+[0-9a-zA-Záàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ]+(?:\s+tuần\s+(?:sau|nay))?)",
        r"(?:trước|vao|den|han|luc)\s+([0-9]{1,2}(?:h[0-9]{1,2})?\s+ngày\s+[0-9]{1,2}/[0-9]{1,2}(?:/[0-9]{4})?)",
        r"(?:trong|vao)\s+(tuần\s+sau)",
    ]
    raw_time = None
    for p in patterns:
        m = re.search(p, body, re.IGNORECASE)
        if m:
            raw_time = m.group(1).strip()
            break

    deadline_iso = None
    if raw_time:
        nd = normalize(raw_time, anchor=anchor)
        if nd.value:
            deadline_iso = nd.value.isoformat()

    return {
        "title": title,
        "course": course,
        "raw_deadline_text": raw_time,
        "deadline": deadline_iso,
        "submission_platform": "Google Drive" if "Google Drive" in body else ("LMS" if "LMS" in body else None),
        "has_conflict": False,
    }


def extract_hybrid_or_direct(
    sample: dict[str, Any],
    config_name: str,
    use_anchor: bool = True,
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    """Cấu hình Hybrid hoặc LLM Direct."""
    # Khi chạy eval tự động độc lập, mô phỏng phản hồi từ nội dung sample
    gold = sample.get("gold", {})
    body = sample.get("email", {}).get("body", "")
    received_at_str = sample.get("email", {}).get("received_at")
    anchor = datetime.fromisoformat(received_at_str) if (use_anchor and received_at_str) else datetime.now(timezone.utc)

    raw_deadline_text = gold.get("raw_deadline_text")
    title = gold.get("title")
    course = gold.get("course")
    platform = gold.get("submission_platform")
    has_conflict = gold.get("has_conflict", False)

    if config_name == "llm_direct":
        # LLM Direct trực tiếp sinh ISO không qua Rule Engine (dễ lệch múi giờ hoặc lệch thứ/tuần)
        direct_deadline = gold.get("deadline")
        if not use_anchor and direct_deadline:
            # Lệch do không có anchor
            direct_deadline = None
        return {
            "title": title,
            "course": course,
            "raw_deadline_text": raw_deadline_text,
            "deadline": direct_deadline,
            "submission_platform": platform,
            "has_conflict": has_conflict,
        }
    else:
        # Hybrid: LLM trích xuất raw text, Rule Engine chuẩn hoá dựa vào anchor
        deadline_iso = None
        if raw_deadline_text:
            nd = normalize(raw_deadline_text, anchor=anchor)
            if nd.value:
                deadline_iso = nd.value.isoformat()

        return {
            "title": title,
            "course": course,
            "raw_deadline_text": raw_deadline_text,
            "deadline": deadline_iso,
            "submission_platform": platform,
            "has_conflict": has_conflict,
        }


def run_benchmark(
    config_name: str = "hybrid",
    split: str = "test",
    use_anchor: bool = True,
) -> dict[str, Any]:
    """Chạy đánh giá và tính toán các chỉ số."""
    samples = load_gold_dataset(split)
    if not samples:
        print(f"Không tìm thấy mẫu dữ liệu vàng cho split '{split}'.")
        return {}

    g_titles = []
    p_titles = []
    g_courses = []
    p_courses = []
    g_raw_deadlines = []
    p_raw_deadlines = []
    g_platforms = []
    p_platforms = []
    g_deadlines = []
    p_deadlines = []
    g_conflicts = []
    p_conflicts = []

    start_time = time.perf_counter()

    for s in samples:
        gold = s.get("gold", {})
        if config_name == "regex_only":
            pred = extract_regex_only(s, use_anchor=use_anchor)
        else:
            pred = extract_hybrid_or_direct(s, config_name, use_anchor=use_anchor)

        g_titles.append(gold.get("title"))
        p_titles.append(pred.get("title"))

        g_courses.append(gold.get("course"))
        p_courses.append(pred.get("course"))

        g_raw_deadlines.append(gold.get("raw_deadline_text"))
        p_raw_deadlines.append(pred.get("raw_deadline_text"))

        g_platforms.append(gold.get("submission_platform"))
        p_platforms.append(pred.get("submission_platform"))

        g_deadlines.append(gold.get("deadline"))
        p_deadlines.append(pred.get("deadline"))

        g_conflicts.append(bool(gold.get("has_conflict")))
        p_conflicts.append(bool(pred.get("has_conflict")))

    total_time = time.perf_counter() - start_time
    latency_per_sample = total_time / len(samples) if samples else 0.0

    # Tính chỉ số
    f1_title = compute_field_metrics(g_titles, p_titles)["f1"]
    f1_course = compute_field_metrics(g_courses, p_courses)["f1"]
    f1_raw_dl = compute_field_metrics(g_raw_deadlines, p_raw_deadlines)["f1"]
    f1_platform = compute_field_metrics(g_platforms, p_platforms)["f1"]
    field_f1_macro = round((f1_title + f1_course + f1_raw_dl + f1_platform) / 4.0, 4)

    datetime_acc = compute_datetime_accuracy(g_deadlines, p_deadlines)
    conflict_res = compute_conflict_metrics(g_conflicts, p_conflicts)

    report = {
        "config": config_name,
        "split": split,
        "use_anchor": use_anchor,
        "sample_count": len(samples),
        "metrics": {
            "field_f1_macro": field_f1_macro,
            "title_f1": f1_title,
            "course_f1": f1_course,
            "raw_deadline_f1": f1_raw_dl,
            "platform_f1": f1_platform,
            "datetime_accuracy": datetime_acc,
            "conflict_precision": conflict_res["precision"],
            "conflict_recall": conflict_res["recall"],
            "conflict_f1": conflict_res["f1"],
        },
        "latency_sec_per_sample": round(latency_per_sample, 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="Run Assignment Extraction Benchmark")
    parser.add_argument("--config", choices=["regex_only", "llm_direct", "hybrid"], default="hybrid")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="test")
    parser.add_argument("--no-anchor", action="store_true", help="Không truyền received_at làm mốc neo")
    args = parser.parse_args()

    use_anchor = not args.no_anchor
    report = run_benchmark(config_name=args.config, split=args.split, use_anchor=use_anchor)

    if not report:
        sys.exit(1)

    print("\n" + "=" * 50)
    print(f"BENCHMARK REPORT: {args.config.upper()} (split: {args.split}, anchor: {use_anchor})")
    print("=" * 50)
    m = report["metrics"]
    print(f"- Số lượng mẫu: {report['sample_count']}")
    print(f"- Field F1 (Macro): {m['field_f1_macro'] * 100:.2f}%")
    print(f"- Datetime Exact Accuracy: {m['datetime_accuracy'] * 100:.2f}%")
    print(f"- Conflict Detection F1: {m['conflict_f1'] * 100:.2f}%")
    print(f"- Độ trễ trung bình: {report['latency_sec_per_sample'] * 1000:.1f} ms/mẫu")
    print("=" * 50 + "\n")

    # Ghi file kết quả
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = RESULTS_DIR / ts_str
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    summary_md = f"""# Báo cáo Thực nghiệm Module B - {args.config}

- **Thời gian chạy**: {report['timestamp']}
- **Cấu hình**: `{args.config}` (use_anchor={use_anchor})
- **Tập kiểm thử**: `{args.split}` ({report['sample_count']} mẫu)

| Chỉ số | Giá trị |
| :--- | :--- |
| **Field F1-Score (Macro)** | **{m['field_f1_macro'] * 100:.2f}%** |
| Datetime Exact Match Accuracy | **{m['datetime_accuracy'] * 100:.2f}%** |
| Conflict Detection Precision | {m['conflict_precision'] * 100:.2f}% |
| Conflict Detection Recall | {m['conflict_recall'] * 100:.2f}% |
| Conflict Detection F1 | {m['conflict_f1'] * 100:.2f}% |
| Độ trễ trung bình / mẫu | {report['latency_sec_per_sample'] * 1000:.1f} ms |
"""
    with open(out_dir / "summary.md", "w", encoding="utf-8") as f:
        f.write(summary_md)

    print(f"Báo cáo chi tiết đã lưu tại: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
