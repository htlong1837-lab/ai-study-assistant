from __future__ import annotations

import hashlib
import unicodedata
from typing import List
from uuid import uuid4

from citation_verifier import validate_answer
from errors import MissingAPIKeyError
from llm_client import LLMClient
from models.answer import Answer
from models.citation import Citation
from models.document import ParsedDocument
from services.validation import validate_parsed_document, validate_question


class QAService:
    """Orchestrates document parsing, LLM querying, and answer validation.

    API key resolution (L1 / L2 fix)
    ----------------------------------
    *   The caller is responsible for providing the API key.
    *   The UI layer (``streamlit_app.py``) resolves the effective key
        (user-supplied or host default) and passes it here.
    *   ``QAService`` never reads ``os.getenv`` or ``st.secrets`` directly.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        api_key: str | None = None,
    ) -> None:
        if llm_client is not None:
            self.llm_client = llm_client
        elif api_key:
            self.llm_client = LLMClient(api_key=api_key)
        else:
            raise MissingAPIKeyError(
                "QAService requires either an LLMClient instance or a non-empty api_key."
            )

    @staticmethod
    def _make_question_id(question: str) -> str:
        """Return a stable, Unicode-normalised hash for *question*."""
        # NFC normalisation ensures that visually identical Vietnamese text
        # (typed as precomposed NFC or decomposed NFD) maps to the same ID.
        normalised = " ".join(
            unicodedata.normalize("NFC", question.strip().lower()).split()
        )
        return "q-" + hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:12]

    def ask_question(
        self,
        document: ParsedDocument,
        question: str,
        reference_material: bool = True,
    ) -> Answer:
        if not validate_question(question):
            raise ValueError("Question text cannot be empty.")
        warnings = validate_parsed_document(document)
        if warnings:
            raise ValueError("Invalid document: " + "; ".join(warnings))

        page_texts = document.page_texts()
        result = self.llm_client.generate_answer(
            question, page_texts, reference_material=reference_material
        )

        citations: List[Citation] = [
            Citation(
                page_num=item["page_num"],
                evidence_text=item["evidence_text"],
                confidence=item.get("confidence", 1.0),
            )
            for item in result.get("citations", [])
        ]

        # answer_id: unique per response (uuid4 suffix prevents ID collision)
        answer_id = f"answer-{document.doc_id}-{uuid4().hex[:12]}"
        question_id = self._make_question_id(question)

        answer = Answer(
            answer_id=answer_id,
            doc_id=document.doc_id,
            question_id=question_id,
            text=result.get("answer", ""),
            citations=citations,
            status="draft",
            source=result.get("source", "llm"),
            model_used=result.get("model_used"),
        )

        valid, val_warnings = validate_answer(document, answer)
        if not valid:
            answer.status = "rejected"
            raise ValueError(
                "Unsupported citations were found: " + "; ".join(val_warnings)
            )

        answer.status = "verified"
        return answer
