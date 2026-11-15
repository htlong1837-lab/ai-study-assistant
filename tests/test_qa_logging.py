import json
import io
import logging

from modules.qa.structured_logging import log_qa_event, mask_secrets, qa_logger


def test_secret_masking_covers_supported_key_shapes():
    assert mask_secrets("problem AIza" + "A" * 35) == "problem [REDACTED]"
    assert "sk-" not in mask_secrets("sk-" + "b" * 32)


def test_structured_log_has_metrics_but_no_prompt_or_answer():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = qa_logger()
    logger.addHandler(handler)
    log_qa_event(
        doc_id="doc-safe",
        question_id="q-safe",
        model_used="model-safe",
        source="llm",
        latency_ms=12.345,
        status="verified",
    )
    logger.removeHandler(handler)
    output = stream.getvalue().strip()
    data = json.loads(output)
    assert data["doc_id"] == "doc-safe"
    assert data["latency_ms"] == 12.35
    assert "prompt" not in output.lower()
    assert "answer text" not in output.lower()
