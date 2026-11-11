from __future__ import annotations

import argparse
import getpass
import json
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.llm_client import LLMClient  # noqa: E402
from modules.qa.benchmark import validate_dataset  # noqa: E402
from modules.qa.citation_verifier import verify_citations  # noqa: E402
from modules.qa.qa_service import QAService  # noqa: E402
from modules.qa.text_normalize import normalize  # noqa: E402


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(
        0, min(len(ordered) - 1, int((pct / 100) * len(ordered) + 0.999999) - 1)
    )
    return round(ordered[index], 2)


def summarize(entries: list[dict]) -> dict:
    good = [entry for entry in entries if "error" not in entry]
    answerable = [entry for entry in good if entry["type"] != "unanswerable"]
    unanswerable = [entry for entry in good if entry["type"] == "unanswerable"]
    abstentions = [entry for entry in good if entry["abstained"]]
    gold_evidence_items = [
        entry["gold_evidence_hit_rate"]
        for entry in answerable
        if entry["gold_evidence_hit_rate"] is not None
    ]
    page_hits = [
        entry["page_hit_rate"]
        for entry in answerable
        if entry["page_hit_rate"] is not None
    ]
    latencies = [entry["latency_ms"] for entry in good]
    return {
        "records": len(good),
        "answer_exact_match": round(
            sum(e["answer_exact_match"] for e in answerable) / len(answerable), 4
        )
        if answerable
        else None,
        "page_hit_rate": round(statistics.mean(page_hits), 4) if page_hits else None,
        "gold_evidence_verbatim_rate": round(statistics.mean(gold_evidence_items), 4)
        if gold_evidence_items
        else None,
        "citation_verbatim_record_rate": round(
            sum(e["citations_verbatim"] for e in answerable) / len(answerable), 4
        )
        if answerable
        else None,
        "abstain_precision": round(
            sum(e["type"] == "unanswerable" for e in abstentions) / len(abstentions), 4
        )
        if abstentions
        else None,
        "unanswerable_abstain_rate": round(
            sum(e["abstained"] for e in unanswerable) / len(unanswerable), 4
        )
        if unanswerable
        else None,
        "fallback_rate": round(
            sum(e["source"] == "local_fallback" for e in good) / len(good), 4
        )
        if good
        else None,
        "latency_p50_ms": percentile(latencies, 50),
        "latency_p95_ms": percentile(latencies, 95),
        "cost_total": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the human-reviewed Module A document QA benchmark."
    )
    parser.add_argument(
        "--dataset", default=str(ROOT / "benchmarks" / "qa" / "dataset.jsonl")
    )
    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to the private source PDF; it is not copied to the report.",
    )
    parser.add_argument(
        "--api-key", help="Gemini API key; omit to enter it through a hidden prompt."
    )
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument(
        "--output", help="Report path; defaults to ignored benchmarks/qa/results/."
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.is_file():
        print(f"DATASET ERROR: file not found: {dataset_path}", file=sys.stderr)
        print(
            "Copy benchmarks/qa/dataset.template.jsonl to benchmarks/qa/dataset.jsonl, then fill and review all gold fields.",
            file=sys.stderr,
        )
        return 2
    validation = validate_dataset(args.dataset, full=True)
    if not validation.valid:
        for error in validation.errors:
            print("DATASET ERROR: " + error, file=sys.stderr)
        return 2
    if validation.pending:
        print(
            f"Dataset still has {len(validation.pending)} record(s) pending human review; benchmark stopped.",
            file=sys.stderr,
        )
        return 2
    key = args.api_key or getpass.getpass("Gemini API key (hidden): ").strip()
    if not key:
        print("An API key is required to run model evaluation.", file=sys.stderr)
        return 2

    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        print(f"PDF ERROR: file not found: {pdf_path}", file=sys.stderr)
        return 2
    from modules.qa.loader import load_document_bytes

    document = load_document_bytes(
        pdf_path.name, pdf_path.read_bytes(), doc_id="benchmark-source"
    )
    for item in validation.records:
        for page_num in item["gold_pages"]:
            if page_num > len(document.pages):
                print(
                    f"{item['id']}: gold page {page_num} exceeds PDF page count {len(document.pages)}",
                    file=sys.stderr,
                )
                return 2
        if item["type"] == "passage" and item["passage_page"] > len(document.pages):
            print(
                f"{item['id']}: passage_page exceeds PDF page count {len(document.pages)}",
                file=sys.stderr,
            )
            return 2
        if item["type"] == "passage" and normalize(
            item["passage_text"]
        ) not in normalize(document.pages[item["passage_page"] - 1].text):
            print(
                f"{item['id']}: passage_text not found on passage_page in the supplied PDF",
                file=sys.stderr,
            )
            return 2
        if item["type"] != "unanswerable":
            source_pages = [
                document.pages[page - 1].text for page in item["gold_pages"]
            ]
            if any(
                not any(
                    normalize(evidence) in normalize(page_text)
                    for page_text in source_pages
                )
                for evidence in item["gold_evidence"]
            ):
                print(
                    f"{item['id']}: at least one gold_evidence excerpt was not found on its gold_pages",
                    file=sys.stderr,
                )
                return 2

    service = QAService(LLMClient(provider="gemini", model=args.model, api_key=key))
    entries = []
    for item in validation.records:
        started = time.perf_counter()
        try:
            if item["type"] == "passage":
                answer = service.ask_about_selection(
                    document,
                    item["passage_page"],
                    item["passage_text"],
                    action="custom",
                    custom_question=item["question"],
                )
            else:
                answer = service.ask_question(document, item["question"])
            valid_citations, _warnings = (
                verify_citations(document, answer.citations)
                if answer.citations
                else (False, ["NO_CITATION"])
            )
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            cited_pages = {citation.page_num for citation in answer.citations}
            gold_pages = set(item["gold_pages"])
            gold_evidence = [normalize(ev) for ev in item["gold_evidence"]]
            cited_evidence = [normalize(c.evidence_text) for c in answer.citations]
            evidence_hits = sum(
                any(ev and (ev in cited or cited in ev) for cited in cited_evidence)
                for ev in gold_evidence
            )
            answer_match = normalize(answer.text) == normalize(item["gold_answer"])
            abstained = (not answer.can_answer) or (answer.status == "rejected")
            entries.append(
                {
                    "id": item["id"],
                    "type": item["type"],
                    "status": answer.status,
                    "source": answer.source,
                    "abstained": abstained,
                    "answer_exact_match": answer_match,
                    "page_hit_rate": (len(cited_pages & gold_pages) / len(gold_pages))
                    if gold_pages
                    else None,
                    "gold_evidence_hit_rate": (evidence_hits / len(gold_evidence))
                    if gold_evidence
                    else None,
                    "citations_verbatim": bool(valid_citations),
                    "latency_ms": elapsed,
                }
            )
        except Exception as exc:
            entries.append(
                {"id": item["id"], "type": item["type"], "error": type(exc).__name__}
            )

    groups = {
        kind: summarize([entry for entry in entries if entry["type"] == kind])
        for kind in ("whole_document", "passage", "unanswerable")
    }
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "model": args.model,
        "source_filename": pdf_path.name,
        "metrics_by_type": groups,
        "records": entries,
        "errors": sum("error" in entry for entry in entries),
        "metric_notes": {
            "answer_exact_match": "literal normalized exact match; not semantic judging",
            "cost_total": "not measured; model pricing was not verified",
        },
    }
    output = (
        Path(args.output)
        if args.output
        else ROOT
        / "benchmarks"
        / "qa"
        / "results"
        / f"run-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(groups, ensure_ascii=False, indent=2))
    print(f"Report saved to {output}")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
