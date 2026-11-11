from scripts.run_qa_benchmark import percentile, summarize


def test_percentile_nearest_rank_and_empty_values():
    assert percentile([], 95) is None
    assert percentile([10, 20, 30, 40], 50) == 20
    assert percentile([10, 20, 30, 40], 95) == 40


def test_summary_separates_unanswerable_and_abstention_metrics():
    records = [
        {
            "id": "a",
            "type": "passage",
            "answer_exact_match": True,
            "page_hit_rate": 1.0,
            "gold_evidence_hit_rate": 1.0,
            "citations_verbatim": True,
            "abstained": False,
            "source": "llm",
            "latency_ms": 100,
        },
        {
            "id": "u",
            "type": "unanswerable",
            "answer_exact_match": False,
            "page_hit_rate": None,
            "gold_evidence_hit_rate": None,
            "citations_verbatim": False,
            "abstained": True,
            "source": "llm",
            "latency_ms": 200,
        },
    ]
    result = summarize(records)
    assert result["answer_exact_match"] == 1.0
    assert result["unanswerable_abstain_rate"] == 1.0
    assert result["abstain_precision"] == 1.0
    assert result["citation_verbatim_record_rate"] == 1.0
    assert result["cost_total"] is None
