# Implementation Plan: Document Q&A via API

**Branch**: `001-document-qna-api` | **Date**: 2026-11-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-document-qna-api/spec.md`

## Summary

This feature delivers a secure document Q&A workflow for Module A: ingest PDF content, normalize it into page-level source data, answer questions with page citations, enforce citation verification before display, and provide a Streamlit interface plus evaluation tooling. The design centers on a shared LLM wrapper, a direct document-processing pipeline, and a single validated document contract that preserves `doc_id`, source context, and page evidence.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: PyMuPDF, Streamlit, Python standard library, LLM provider SDKs, testing with pytest

**Storage**: In-memory or file-based caching for LLM responses; no dedicated persistent database required for v1; document text stored in-process or via existing secure intake pipeline

**Testing**: pytest for unit/integration checks; evaluation run scripts and benchmark assertions for citation accuracy

**Target Platform**: Local desktop/server deployment with Streamlit UI and PDF processing on a Python backend

**Project Type**: Web application (Streamlit UI) with supporting Python service modules

**Performance Goals**: Answer standard document questions within 2 minutes; support repeated requests with cache reuse; maintain clear citation validation feedback during Q&A

**Constraints**: Must preserve secure document contract; page citations must be validated against source text; no vector database or retrieval-layer architecture; citation failures must block answer display

**Scale/Scope**: Initial scope covers secure PDF intake, page-level extraction, LLM Q&A with evidence checks, UI navigation, and benchmark evaluation on a fixed set of 30 questions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Pass: Direct document processing is used; no vector database or RAG layer is introduced.
- Pass: All AI access goes through a centralized `llm_client.py` wrapper for token counting, cost tracking, and caching.
- Pass: The document contract preserves `file_path`, `doc_id`, and optional `source_email_id`, and returns a normalized `ParsedDocument` with page text.
- Pass: Every answer is required to include source-backed citations and cannot be shown without verification.
- Pass: Cost-aware execution is treated as a first-class requirement with cache reuse and telemetry.
- Pass: Streamlit integration and Python-only implementation are consistent with the constitution.
- Pass: Evaluation and UI flows both preserve the citation-first evidence requirement.

## Project Structure

### Documentation (this feature)

```text
specs/001-document-qna-api/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── spec.md              # Feature specification
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (not yet created)
```

### Source Code (repository root)

```text
src/
├── llm_client.py
├── document_parser.py
├── qa_service.py
├── citation_verifier.py
├── streamlit_app.py
├── models/
│   ├── document.py
│   ├── page.py
│   ├── answer.py
│   └── citation.py
├── services/
│   ├── pdf_loader.py
│   ├── evaluation_runner.py
│   └── cache_manager.py
└── tests/
    ├── unit/
    ├── integration/
    └── benchmark/
```

**Structure Decision**: A single Python service layer plus Streamlit frontend is sufficient because the feature is a focused document Q&A application rather than a distributed system. The document-processing and QA logic are centralized in `src/` while the UI remains a thin presentation layer.

## Complexity Tracking

No constitution violations require justification. The design remains within the approved governance model and avoids unnecessary architectural expansion.
