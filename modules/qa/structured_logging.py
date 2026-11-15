from __future__ import annotations

import json
import logging
import re

_SECRET_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"AQ\.[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
)


def mask_secrets(value: str) -> str:
    text = value or ""
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def qa_logger() -> logging.Logger:
    logger = logging.getLogger("module_a.qa")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_qa_event(
    *,
    doc_id: str,
    question_id: str,
    model_used: str | None,
    source: str,
    latency_ms: float,
    status: str,
    cost: float | None = None,
) -> None:
    event = {
        "doc_id": mask_secrets(doc_id),
        "question_id": question_id,
        "model_used": mask_secrets(model_used or ""),
        "source": source,
        "latency_ms": round(latency_ms, 2),
        "cost": cost,
        "status": status,
    }
    qa_logger().info(json.dumps(event, ensure_ascii=False, separators=(",", ":")))


def log_qa_error(
    *,
    doc_id: str,
    question_id: str,
    model_used: str | None,
    latency_ms: float,
    error: Exception,
) -> None:
    event = {
        "doc_id": mask_secrets(doc_id),
        "question_id": question_id,
        "model_used": mask_secrets(model_used or ""),
        "source": "llm",
        "latency_ms": round(latency_ms, 2),
        "cost": None,
        "status": "error",
        "error_type": type(error).__name__,
    }
    qa_logger().warning(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
