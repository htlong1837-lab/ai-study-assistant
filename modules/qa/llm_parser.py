from __future__ import annotations

import json
import re


def parse_llm_response(raw: str) -> dict:
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("LLM response did not contain a JSON object")
    payload = re.sub(r",\s*([}\]])", r"\1", text[start : end + 1])
    data = json.loads(payload)
    if not isinstance(data, dict) or not isinstance(data.get("answer", ""), str):
        raise ValueError("Invalid answer schema")
    citations = data.get("citations", [])
    if "can_answer" in data and not isinstance(data["can_answer"], bool):
        raise ValueError("can_answer must be a boolean")
    if not isinstance(citations, list):
        raise ValueError("citations must be a list")
    for item in citations:
        if (
            not isinstance(item, dict)
            or type(item.get("page_num")) is not int
            or item["page_num"] < 1
            or not isinstance(item.get("evidence_text", ""), str)
        ):
            raise ValueError("Invalid citation schema")
    return {
        "can_answer": bool(data.get("can_answer", True)),
        "answer": data.get("answer", ""),
        "citations": citations,
        "background_note": str(data.get("background_note", "")),
    }
