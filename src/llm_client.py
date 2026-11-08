from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, Sequence

from errors import LLMUnavailableError, MissingAPIKeyError, ModuleAError
from utils.security import mask_secrets

try:
    import config
except ImportError:  # pragma: no cover
    config = None


class LLMClient:
    """Thin LLM wrapper for token counting, cost tracking, cache reuse, and Gemini API calls.

    API key contract
    ----------------
    *   The caller is responsible for supplying a non-empty ``api_key``.
    *   This class does **not** read ``os.getenv``, ``st.secrets``, or any
        file on disk.  Key resolution belongs to the application layer
        (``streamlit_app.py`` or the CLI), not to the library.
    *   Passing an empty / ``None`` key raises :exc:`MissingAPIKeyError`
        immediately so the error surfaces at construction time, not deep
        inside a network call.
    """

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        cache_dir: str | None = None,
    ) -> None:
        if not api_key or not str(api_key).strip():
            raise MissingAPIKeyError(
                "API key is required. "
                "Please provide a valid Gemini API key for this session. "
                "Get a free key at https://aistudio.google.com/"
            )
        self.api_key: str = str(api_key).strip()
        self.model: str = model or "gemini-2.5-flash"
        # Lazy initialisation: the directory is created only when _write_cache
        # is first called, so constructing LLMClient has zero disk side-effects.
        self._cache_dir_path: Path = Path(cache_dir or ".cache/llm")
        self._cache_dir_ready: bool = False

        self.model_prices: Dict[str, Dict[str, float]] = {
            # --- Paid / High-Intelligence models ---
            "gemini-4-argon":  {"input": 2.00 / 1_000, "output": 10.00 / 1_000},
            "gemini-3.8-flash": {"input": 0.15 / 1_000, "output": 0.60 / 1_000},
            # --- Free-Tier models ---
            "gemini-2.5-flash": {"input": 0.075 / 1_000, "output": 0.30 / 1_000},
            "gemini-2.0-flash": {"input": 0.075 / 1_000, "output": 0.30 / 1_000},
            "gemini-1.5-flash": {"input": 0.075 / 1_000, "output": 0.30 / 1_000},
            "gemini-1.5-pro":   {"input": 0.35  / 1_000, "output": 1.05  / 1_000},
        }

    # ------------------------------------------------------------------
    # Token / cost helpers
    # ------------------------------------------------------------------

    @staticmethod
    def count_tokens(text: str) -> int:
        if not text:
            return 0
        return len(re.findall(r"\S+", text))

    def estimate_cost(self, input_tokens: int, output_tokens: int = 0) -> float | None:
        if config is not None:
            c = config.estimate_cost(self.model, input_tokens, output_tokens)
            if c is not None:
                return c
        pricing = self.model_prices.get(self.model, {"input": 0.0, "output": 0.0})
        return round(
            (input_tokens / 1000.0) * pricing["input"]
            + (output_tokens / 1000.0) * pricing["output"],
            6,
        )

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def build_prompt(
        self,
        question: str,
        page_texts: Sequence[dict],
        reference_material: bool = True,
    ) -> str:
        normalized_pages: list[str] = []
        for page in page_texts:
            if isinstance(page, dict):
                page_num = page.get("page_num")
                page_text = page.get("text", "")
            else:
                page_num = getattr(page, "page_num", None)
                page_text = getattr(page, "text", "")
            page_text = str(page_text or "").strip()
            if page_num is None:
                continue
            normalized_pages.append(f"Page {page_num}\n{page_text}")

        context = "\n\n".join(normalized_pages)
        if not context:
            raise ValueError("No document pages were provided to the LLM client.")

        reference_instruction = (
            "Use the document passages below as the only evidence. "
            "Combine relevant facts across pages to form a coherent synthesis "
            "when the question is broader than a single fact."
            if reference_material
            else "Answer only from the provided document pages; do not infer or invent information."
        )

        return (
            "You are a precise document analyst. Read every provided page carefully and "
            "synthesize the information into a clear, coherent answer. "
            "Do not simply copy a single sentence. Instead, combine the relevant facts "
            "across pages to explain the question in context when needed. "
            "Only use information explicitly supported by the supplied document excerpts. "
            "If the question is broad, provide an explanation that logically connects "
            "relevant ideas across the source pages. "
            "If the source does not contain enough support, say that clearly rather than guessing. "
            "Every factual claim in the answer must be backed by the source pages and must include "
            "a citation in the form [Page N] or [Page N, M]. "
            "Citations should reflect the exact pages that support the claim. "
            "Return valid JSON only with keys 'answer' and 'citations'. "
            "'answer' must be a concise but complete explanatory response grounded in the document. "
            "'citations' must be a list of integers representing the supporting pages.\n\n"
            f"{reference_instruction}\n\n"
            "Instructions for output:\n"
            "- Explain the concept or answer in a natural, coherent way when the question is broad.\n"
            "- Use the document passages as the source of truth.\n"
            "- Do not use outside knowledge or assumptions.\n"
            "- Do not invent page numbers or unsupported facts.\n"
            "- Cite the relevant pages that support each answer segment.\n\n"
            f"Question: {question}\n\n"
            "Document source pages:\n"
            f"{context}"
        )

    # ------------------------------------------------------------------
    # Cache helpers  (lazy directory creation)
    # ------------------------------------------------------------------

    def cache_key(
        self,
        question: str,
        page_texts: Sequence[dict],
        reference_material: bool,
    ) -> str:
        content = json.dumps(
            {
                "question": question,
                "reference_material": reference_material,
                "page_texts": page_texts,
                "model": self.model,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _ensure_cache_dir(self) -> None:
        """Create the cache directory on first write (lazy side-effect)."""
        if not self._cache_dir_ready:
            self._cache_dir_path.mkdir(parents=True, exist_ok=True)
            self._cache_dir_ready = True

    def _read_cache(self, key: str) -> Dict[str, Any] | None:
        cache_path = self._cache_dir_path / f"{key}.json"
        if not cache_path.exists():
            return None
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def _write_cache(self, key: str, payload: Dict[str, Any]) -> None:
        self._ensure_cache_dir()
        cache_path = self._cache_dir_path / f"{key}.json"
        cache_path.write_text(
            json.dumps(payload, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Citation extraction / fallback
    # ------------------------------------------------------------------

    def _extract_page_citations(
        self, response_text: str, page_texts: Sequence[dict]
    ) -> list[dict[str, Any]]:
        page_numbers: list[int] = []
        for match in re.finditer(r"(?i)(?:\[\s*|\bpage\s*(?:#\s*)?)(\\d+)\b", response_text):
            page_num = int(match.group(1))
            if page_num not in page_numbers:
                page_numbers.append(page_num)

        page_lookup = {int(page["page_num"]): page for page in page_texts}
        citations: list[dict[str, Any]] = []
        for page_num in page_numbers:
            page = page_lookup.get(page_num)
            if page is None:
                continue
            snippet = str(page.get("text", "")).strip()
            if snippet:
                snippet = "\n".join(snippet.splitlines()[:2])[:180]
            citations.append(
                {
                    "page_num": page_num,
                    "evidence_text": snippet or "Source text support",
                    "confidence": 1.0,
                }
            )
        return citations

    def _fallback_answer(
        self, question: str, page_texts: Sequence[dict]
    ) -> tuple[str, list[dict[str, Any]]]:
        normalized_question = re.sub(r"[^a-z0-9]+", " ", (question or "").lower()).split()
        scored_pages: list[tuple[float, dict[str, Any]]] = []

        for page in page_texts:
            text = str(page.get("text", ""))
            tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
            token_set = set(tokens)
            overlap = sum(1 for word in normalized_question if word in token_set)
            if overlap == 0:
                overlap = 0.1
            scored_pages.append((float(overlap), page))

        scored_pages.sort(key=lambda item: item[0], reverse=True)
        best_page = scored_pages[0][1] if scored_pages else {"page_num": 1, "text": ""}
        page_text = str(best_page.get("text", "")).strip()
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", page_text)
            if s.strip()
        ]
        answer_text = (
            sentences[0]
            if sentences
            else page_text
            or "The source text does not provide enough information to answer this question confidently."
        )

        evidence = [
            {
                "page_num": int(best_page.get("page_num", 1)),
                "evidence_text": answer_text,
                "confidence": 1.0,
            }
        ]
        return answer_text, evidence

    # ------------------------------------------------------------------
    # Model cascade
    # ------------------------------------------------------------------

    def _candidate_models(self) -> list[str]:
        """Return an ordered list of models to try, starting with self.model."""
        if config is not None:
            configured_cascade = config.get_model_cascade()
        else:
            configured_cascade = [
                "gemini-4-argon",
                "gemini-3.8-flash",
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
            ]
        ordered: list[str] = [self.model]
        seen: set[str] = {self.model}
        for candidate in configured_cascade:
            if candidate and candidate not in seen:
                seen.add(candidate)
                ordered.append(candidate)
        return ordered

    # ------------------------------------------------------------------
    # LLM invocation
    # ------------------------------------------------------------------

    # Errors that justify trying the next model in the cascade instead of
    # propagating immediately.
    _CASCADE_CONTINUE_SIGNALS = (
        "not found",
        "unsupported",
        "404",
        "503",
        "service unavailable",
        "billing",
        "timeout",
        "timed out",
        "deadline",
    )

    def _invoke_llm(self, prompt: str) -> tuple[str, str]:
        """Call Gemini and return ``(response_text, model_name_used)``.

        Iterates through the cascade and returns the first successful result.
        Raises :exc:`LLMUnavailableError` if every model fails.
        """
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

        last_exc: Exception | None = None
        for candidate_model in self._candidate_models():
            try:
                logging.info("[LLMClient] Trying model '%s'…", candidate_model)
                try:
                    from google import genai  # type: ignore[import-untyped]
                except ImportError:
                    genai = None  # type: ignore[assignment]

                if genai is not None:
                    client = genai.Client(
                        api_key=self.api_key,
                        http_options={"timeout": 15_000},
                    )
                    response = client.models.generate_content(
                        model=candidate_model, contents=prompt
                    )
                    text = getattr(response, "text", "") or ""
                    if not text:
                        for cand in getattr(response, "candidates", []) or []:
                            content = getattr(cand, "content", None)
                            for part in getattr(content, "parts", []) or []:
                                text += getattr(part, "text", "") or ""
                    if text:
                        logging.info(
                            "[LLMClient] Response received from '%s'.", candidate_model
                        )
                        return text.strip(), candidate_model

                try:
                    import google.generativeai as generative_ai  # type: ignore[import-untyped]
                except ImportError as exc:
                    raise RuntimeError(
                        "The Gemini library is required. "
                        "Install 'google-genai' or 'google-generativeai'."
                    ) from exc

                generative_ai.configure(api_key=self.api_key)
                gai_model = generative_ai.GenerativeModel(candidate_model)
                response = gai_model.generate_content(prompt)
                text = getattr(response, "text", str(response)).strip()
                if text:
                    logging.info(
                        "[LLMClient] Response received from '%s'.", candidate_model
                    )
                    return text, candidate_model

            except Exception as exc:
                last_exc = exc
                message = str(exc).lower()
                logging.warning(
                    "[LLMClient] Model '%s' failed: %s",
                    candidate_model,
                    mask_secrets(str(exc)),
                )

                if "quota" in message or "credit" in message or "limit" in message:
                    raise RuntimeError(
                        "Your Gemini API account has no remaining quota or credits. "
                        "Add credits or use a different key."
                    ) from exc
                if "api key" in message or "authentication" in message or "unauthorized" in message:
                    from errors import InvalidAPIKeyError
                    raise InvalidAPIKeyError(
                        "The Gemini API key is invalid or expired. "
                        "Please provide a valid key."
                    ) from exc

                # Cascade-continue conditions: try next model
                if any(signal in message for signal in self._CASCADE_CONTINUE_SIGNALS):
                    logging.warning(
                        "[LLMClient] Cascading to next model (reason: %s).",
                        mask_secrets(message[:120]),
                    )
                    continue

                # Unknown error — stop cascade and propagate
                raise RuntimeError(
                    f"Gemini API request failed: {mask_secrets(str(exc))}"
                ) from exc

        raise LLMUnavailableError(
            "All models in the cascade failed. "
            "Please check your API key, network connection, and model availability. "
            f"Last error: {mask_secrets(str(last_exc))}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_answer(
        self,
        question: str,
        page_texts: Sequence[dict],
        reference_material: bool = True,
    ) -> Dict[str, Any]:
        """Generate an answer and return a payload dict.

        The ``source`` field in the returned payload is one of:
        ``"llm"`` – a live Gemini response (cached after first call),
        ``"cache"`` – loaded from the local cache,
        ``"local_fallback"`` – keyword-search fallback (never cached).
        """
        if not page_texts:
            raise ValueError("No document pages were provided to the LLM client.")

        prompt = self.build_prompt(question, page_texts, reference_material)
        key = self.cache_key(question, page_texts, reference_material)
        cached = self._read_cache(key)
        if cached is not None:
            cached.setdefault("source", "cache")
            cached["source"] = "cache"
            return cached

        try:
            response_text, model_used = self._invoke_llm(prompt)
            response_text = response_text.strip()
            parsed = self._parse_llm_response(response_text)
            answer_text = parsed["answer"]
            citations = parsed["citations"]
            source = "llm"
        except (LLMUnavailableError, RuntimeError, ModuleAError, Exception) as exc:
            logging.warning(
                "[LLMClient] Falling back to local keyword search: %s",
                mask_secrets(str(exc)),
            )
            answer_text, citations = self._fallback_answer(question, page_texts)
            model_used = None
            source = "local_fallback"
        except ValueError as exc:
            logging.warning("[LLMClient] LLM response parsing failed: %s", exc)
            answer_text, citations = self._fallback_answer(question, page_texts)
            model_used = None
            source = "local_fallback"
        else:
            if not citations:
                extracted = self._extract_page_citations(response_text, page_texts)
                citations = extracted if extracted else citations

        if not citations:
            fallback_text, fallback_citations = self._fallback_answer(question, page_texts)
            if fallback_text and fallback_citations:
                answer_text = fallback_text
                citations = fallback_citations

        input_tokens = self.count_tokens(prompt)
        output_tokens = self.count_tokens(answer_text)
        payload: Dict[str, Any] = {
            "answer": answer_text,
            "citations": citations,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": self.estimate_cost(input_tokens, output_tokens),
            "source": source,
            "model_used": model_used,
        }

        # Only persist genuine LLM responses to cache – never fallback results.
        if source == "llm":
            self._write_cache(key, payload)

        return payload

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        raw_text = response_text.strip()
        if not raw_text:
            raise ValueError("LLM returned an empty response.")

        cleaned = (
            raw_text.removeprefix("```json")
            .removeprefix("```JSON")
            .removesuffix("```")
            .strip()
        )
        if cleaned.startswith("{"):
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                answer = str(parsed.get("answer", "")).strip()
                raw_citations = parsed.get("citations", [])
                if answer:
                    normalized: list[dict[str, Any]] = []
                    for item in raw_citations:
                        if isinstance(item, dict):
                            page_num = item.get("page_num")
                            evidence_text = item.get("evidence_text") or answer
                            confidence = item.get("confidence", 1.0)
                        elif isinstance(item, int):
                            page_num = item
                            evidence_text = answer
                            confidence = 1.0
                        else:
                            continue
                        normalized.append(
                            {
                                "page_num": int(page_num),
                                "evidence_text": str(evidence_text),
                                "confidence": float(confidence),
                            }
                        )
                    return {"answer": answer, "citations": normalized}

        answer_match = re.search(
            r'"answer"\s*:\s*"((?:\\.|[^"\\])*)"', cleaned, re.DOTALL
        )
        citations_match = re.search(
            r'"citations"\s*:\s*(\[[^\]]*\])', cleaned, re.DOTALL
        )
        if answer_match:
            answer_text = answer_match.group(1).encode("utf-8").decode("unicode_escape")
            extracted: list[dict[str, Any]] = []
            if citations_match:
                for page_num in re.findall(r"(\d+)", citations_match.group(1)):
                    extracted.append(
                        {
                            "page_num": int(page_num),
                            "evidence_text": answer_text,
                            "confidence": 1.0,
                        }
                    )
            return {"answer": answer_text, "citations": extracted}

        raise ValueError(
            "LLM response was not valid JSON with the required 'answer' and 'citations' fields."
        )
