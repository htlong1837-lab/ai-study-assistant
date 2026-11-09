# Research Notes: Document Q&A via API

## Decision: Direct document processing with page-level citation verification

The feature should process the original PDF text directly and keep the prompt grounded in extracted page content. This matches the constitution’s direct document-processing principle and avoids introducing a retrieval layer or vector database.

## Rationale

- The specification explicitly requires page-based evidence and verification against source text.
- A direct pipeline allows each answer to be traceable to the exact page that was read.
- Centralizing LLM calls through a shared wrapper reduces duplicated token/cost logic and creates a single enforcement point for caching and guardrails.

## Alternatives considered

- Vector/RAG retrieval layer: rejected because the constitution forbids it for this module and it would split the evidence chain from source pages.
- Answer generation without explicit citation checks: rejected because it undermines trust and conflicts with the requirement to block unsupported references.
- UI-only citation logic without a backend verification layer: rejected because page checks must be enforced before display, not merely suggested in the interface.

## Key research findings

- `PyMuPDF` is an appropriate extraction choice for page-by-page text retrieval in a Python application.
- `ParsedDocument` should retain ordered pages with `page_num` and extracted text so the verifier can compare citations to the real content.
- LLM request caching should be keyed by document identity, prompt text, and relevant page text to avoid invalid cache hits.
- A benchmark evaluation should use a fixed question set and score both answer correctness and citation alignment to the extracted source.
