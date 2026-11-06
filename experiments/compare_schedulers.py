"""So sánh EDF và CP-SAT trên các kịch bản có hạt giống.

    python -m experiments.compare_schedulers            # 3 kịch bản × 10 seed
    python -m experiments.compare_schedulers --seeds 3  # chạy nhanh

Ghi vào experiments/results/: runs.csv, summary.md, *.png
"""
from __future__ import annotations

import argparse
import csv
import platform
import statistics
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from modules.scheduler import ALGORITHMS, schedule  # noqa: E402
from modules.scheduler.metrics import daily_hours, short_blocks, validate  # noqa: E402
from modules.scheduler.model import PRIORITY_WEIGHT  # noqa: E402

from .scenarios import SCENARIOS, base_settings, generate, load_ratio, sessions  # noqa: E402

OUT = Path(__file__).resolve().parent / "results"
FIELDS = ["scenario", "seed", "algorithm", "load_ratio", "tasks", "on_time", "missing_h",
          "weighted_missing", "high_missing_h", "conflicts", "peak_h", "load_std", "blocks",
          "short_blocks", "runtime_s", "status"]
METRICS = [  # (cột, nhãn, hướng tốt: -1 = nhỏ hơn tốt)
    ("on_time", "Nhiệm vụ kịp hạn (%)", 1),
    ("missing_h", "Giờ thiếu", -1),
    ("weighted_missing", "Giờ thiếu có trọng số", -1),
    ("high_missing_h", "Giờ thiếu của việc ưu tiên cao", -1),
    ("peak_h", "Đỉnh tải (giờ/ngày)", -1),
    ("load_std", "Độ lệch tải (giờ)", -1),
    ("blocks", "Số khối học", -1),
    ("short_blocks", "Khối < 60 phút", -1),
    ("conflicts", "Xung đột", -1),
    ("runtime_s", "Thời gian chạy (s)", -1),
]


def run_one(name: str, seed: int, algo: str, sess, settings) -> dict:
    tasks = generate(name, seed)
    r = schedule(tasks, sess, settings, algo)
    by_id = {t.id: t for t in tasks}
    load = daily_hours(r.blocks)
    last = max(t.deadline.date() for t in tasks)
    span = [d for d in (settings.start + timedelta(days=i)
                        for i in range(settings.days)) if d <= last]
    per_day = [load.get(d, 0.0) for d in span]
    return {
        "scenario": name, "seed": seed, "algorithm": algo,
        "load_ratio": round(load_ratio(tasks, sess, settings), 3), "tasks": len(tasks),
        "on_time": round(100 * (len(tasks) - len(r.missing_hours)) / len(tasks), 1),
        "missing_h": round(sum(r.missing_hours.values()), 2),
        "weighted_missing": round(sum(PRIORITY_WEIGHT[by_id[k].priority] * v
                                      for k, v in r.missing_hours.items()), 2),
        "high_missing_h": round(sum(v for k, v in r.missing_hours.items()
                                    if by_id[k].priority.value == "high"), 2),
        "conflicts": len(validate(r.blocks, tasks, sess, settings)),
        "peak_h": round(max(per_day), 2),
        "load_std": round(statistics.pstdev(per_day), 3),
        "blocks": len(r.blocks),
        "short_blocks": short_blocks(r.blocks, tasks, settings),
        "runtime_s": round(r.runtime_s, 3),
        "status": r.status,
    }


def mean_std(values: list[float]) -> str:
    m = statistics.mean(values)
    s = statistics.stdev(values) if len(values) > 1 else 0.0
    return f"{m:.2f} ± {s:.2f}"


def summarize(rows: list[dict], seeds: int, time_limit: float) -> str:
    out = [
        "# Kết quả thí nghiệm EDF và CP-SAT",
        "",
        f"Sinh bởi `python -m experiments.compare_schedulers --seeds {seeds} --time-limit "
        f"{time_limit:g}` lúc {datetime.now():%Y-%m-%d %H:%M}, Python {platform.python_version()}, "
        f"{platform.processor() or platform.machine()}.",
        "",
        "Cài đặt chung: 28 ngày từ 09/11/2026, thời khoá biểu mẫu (6 buổi/tuần), khung 7h–22h, "
        "tối đa 4 giờ/ngày, ô 30 phút, khối tối thiểu 60 phút (chỉ CP-SAT áp dụng). "
        "Giá trị: trung bình ± độ lệch chuẩn trên các seed.",
        "",
    ]
    for name in SCENARIOS:
        rs = [r for r in rows if r["scenario"] == name]
        if not rs:
            continue
        ratios = [r["load_ratio"] for r in rs if r["algorithm"] == "EDF"]
        sc = SCENARIOS[name]
        out += [f"## {name} — {sc.n_tasks} nhiệm vụ, tỉ lệ tải {mean_std(ratios)}", "",
                "| Chỉ số | EDF | CP-SAT | CP-SAT thắng / hòa / thua |", "|---|---|---|---|"]
        for col, label, sign in METRICS:
            vals = {a: [r[col] for r in rs if r["algorithm"] == a] for a in ALGORITHMS}
            w = t = l = 0
            for e, c in zip(vals["EDF"], vals["CP-SAT"]):
                diff = (c - e) * sign
                w, t, l = w + (diff > 1e-9), t + (abs(diff) <= 1e-9), l + (diff < -1e-9)
            out.append(f"| {label} | {mean_std(vals['EDF'])} | {mean_std(vals['CP-SAT'])} "
                       f"| {w} / {t} / {l} |")
        statuses = sorted({r["status"] for r in rs if r["algorithm"] == "CP-SAT"})
        out += ["", f"Trạng thái CP-SAT: {', '.join(statuses)}.", ""]
    return "\n".join(out)


def plot(rows: list[dict]) -> list[Path]:
    names = [n for n in SCENARIOS if any(r["scenario"] == n for r in rows)]
    colors = {"EDF": "#8a8f98", "CP-SAT": "#4c78a8"}
    panels = [("weighted_missing", "Giờ thiếu có trọng số"), ("peak_h", "Đỉnh tải (giờ/ngày)"),
              ("load_std", "Độ lệch tải (giờ)"), ("short_blocks", "Khối < 60 phút")]
    fig, axes = plt.subplots(1, len(panels), figsize=(14, 3.6))
    width = 0.38
    for ax, (col, title) in zip(axes, panels):
        for i, algo in enumerate(ALGORITHMS):
            means, errs = [], []
            for n in names:
                v = [r[col] for r in rows if r["scenario"] == n and r["algorithm"] == algo]
                means.append(statistics.mean(v))
                errs.append(statistics.stdev(v) if len(v) > 1 else 0)
            xs = [k + (i - 0.5) * width for k in range(len(names))]
            ax.bar(xs, means, width, yerr=errs, capsize=3, label=algo, color=colors[algo])
        ax.set_xticks(range(len(names)), names)
        ax.set_title(title, fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(frameon=False)
    fig.tight_layout()
    p1 = OUT / "so_sanh_chi_so.png"
    fig.savefig(p1, dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3.4))
    for algo in ALGORITHMS:
        rs = [r for r in rows if r["algorithm"] == algo]
        ax.scatter([r["load_ratio"] for r in rs], [r["weighted_missing"] for r in rs],
                   label=algo, color=colors[algo], alpha=0.75, s=22)
    ax.axvline(1, color="#ccc", lw=1, ls="--")
    ax.set_xlabel("Tỉ lệ tải (giờ cần / giờ có thể học)")
    ax.set_ylabel("Giờ thiếu có trọng số")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    p2 = OUT / "thieu_gio_theo_tai.png"
    fig.savefig(p2, dpi=160)
    plt.close(fig)
    return [p1, p2]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--time-limit", type=float, default=10)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    settings, sess = base_settings(args.time_limit), sessions()
    rows = []
    for name in SCENARIOS:
        for seed in range(args.seeds):
            for algo in ALGORITHMS:
                row = run_one(name, seed, algo, sess, settings)
                rows.append(row)
                print(f"{name:8} seed={seed:2} {algo:6} thiếu={row['missing_h']:5} "
                      f"đỉnh={row['peak_h']:4} khối={row['blocks']:3} {row['runtime_s']:6.2f}s "
                      f"{row['status']}", flush=True)

    with open(OUT / "runs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    (OUT / "summary.md").write_text(summarize(rows, args.seeds, args.time_limit), encoding="utf-8")
    for p in plot(rows):
        print("Đã ghi", p.relative_to(OUT.parent.parent))
    print("Đã ghi experiments/results/runs.csv và summary.md")


if __name__ == "__main__":
    main()
