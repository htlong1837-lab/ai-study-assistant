# Tasks: Document Q&A via API

**Input**: Design documents from `/specs/005-document-qna/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the Python project and shared tooling for the document Q&A feature

- [x] T001 Create the project structure described in the implementation plan under `modules/qa/`, `tests/`, and feature docs
- [x] T002 Initialize Python dependencies for document parsing, Streamlit UI, and validation (`PyMuPDF`, `streamlit`, `pytest`)
- [x] T003 [P] Configure linting and formatting for the Python codebase in the repository root

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that must be complete before any user story can be implemented

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

- [x] T004 Create the secure document intake contract and configuration model in `core/contracts.py` and `modules/qa/models/page.py`
- [x] T005 [P] Implement the shared LLM wrapper skeleton in `core/llm_client.py` for token tracking, cost estimation, and cache keys
- [x] T006 [P] Implement cache persistence and request deduplication logic in `core/llm_client.py`
- [x] T007 Implement application-level error handling and validation utilities in `modules/qa/services/validation.py`
- [x] T008 Create benchmark fixture scaffolding in `tests/benchmark/` for the 30-question evaluation dataset

---

## Phase 3: User Story 1 - Ask a question about a PDF document (Priority: P1) 🎯 MVP

**Goal**: Deliver a trusted document Q&A flow that answers questions with source-backed page citations and blocks unsupported evidence.

**Independent Test**: A user can submit a question about a parsed PDF, receive an answer, and confirm the citations match the underlying page text.

### Implementation for User Story 1

- [x] T009 [P] [US1] Implement page-by-page PDF extraction in `modules/qa/document_parser.py` using the secure `ParsedDocument` structure with ordered pages and `page_num` values
- [x] T010 [P] [US1] Implement `modules/qa/qa_service.py` to combine the user question with relevant page text and send the request through the shared LLM wrapper
- [x] T011 [US1] Implement citation validation and answer rejection logic in `modules/qa/citation_verifier.py` so unsupported or insufficient citations block final display
- [x] T012 [US1] Implement the secure document intake loader in `modules/qa/document_parser.py` to preserve `doc_id`, `file_path`, and `source_email_id` through parsing
- [x] T013 [US1] Add the validation and rejection path for weak evidence in `modules/qa/services/validation.py`, ensuring answers cannot be surfaced without verified page support
- [x] T014 [US1] Add logging and cost visibility for each Q&A request in `core/llm_client.py` and `modules/qa/qa_service.py` to surface token and cache behavior

**Checkpoint**: At this point, User Story 1 should be fully functional and independently testable

---

## Phase 4: User Story 2 - Review and navigate cited evidence in the interface (Priority: P2)

**Goal**: Provide a Streamlit Q&A interface where users can ask questions and click citations to jump to the relevant page in the PDF.

**Independent Test**: A user can enter a question, inspect the answer, click a citation label, and navigate directly to the correct page.

### Implementation for User Story 2

- [x] T015 [P] [US2] Create the Streamlit Q&A interface shell in `views/qa.py` with document selection, question input, and answer display
- [x] T016 [US2] Implement citation label navigation and page jump behavior in `views/qa.py` to open the correct document page behind each citation
- [x] T017 [US2] Add loading, empty-state, and error handling in `views/qa.py` for unsupported citations, missing documents, and incomplete extraction results
- [x] T018 [US2] Connect the UI to the verified answer service and ensure the application only renders `status="verified"` answers in `modules/qa/qa_service.py` and `views/qa.py`

**Checkpoint**: At this point, User Stories 1 and 2 should both work independently

---

## Phase 5: User Story 3 - Evaluate answer quality and citation reliability (Priority: P3)

**Goal**: Run a benchmark evaluation set to compare citation accuracy with and without reference material.

**Independent Test**: A fixed set of 30 benchmark questions can be executed and the system reports citation accuracy and answer quality across both modes.

### Implementation for User Story 3

- [x] T019 [P] [US3] Implement the evaluation runner in `modules/qa/services/evaluation_runner.py` to execute the benchmark question set and capture results per question
- [x] T020 [US3] Implement comparison logic in `modules/qa/services/evaluation_runner.py` for performance with and without reference material, including citation accuracy metrics
- [x] T021 [US3] Create the benchmark summary output and reporting format in `modules/qa/services/evaluation_runner.py` and `tests/benchmark/`
- [x] T022 [US3] Add validation for benchmark completeness and result integrity so the evaluation cannot pass unless citation accuracy is measured against the source content

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improve quality across all stories and validate the feature end-to-end

- [x] T023 [P] Update documentation and validation guidance in `specs/005-document-qna/quickstart.md` to reflect the final flow and acceptance criteria
- [x] T024 Review the secure contract and evidence flow across `modules/qa/models/`, `modules/qa/services/`, and `views/qa.py` to confirm `doc_id`, `source_email_id`, and page checks remain consistent
- [x] T025 Run the end-to-end validation flow from `specs/005-document-qna/quickstart.md` and verify that unsupported citations are rejected and valid citations are accepted
- [x] T026 [P] Review token, cost, and cache metrics across the shared LLM wrapper and confirm the system reduces redundant work without bypassing citation checks

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational completion and should be independently testable from User Story 1
- **User Story 3 (Phase 5)**: Depends on Foundational completion and should be independently testable from prior stories
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - core MVP
- **User Story 2 (P2)**: Can start after Foundational - user experience and navigation
- **User Story 3 (P3)**: Can start after Foundational - evaluation and benchmarking

### Parallel Opportunities

- T002 and T003 can run in parallel during Setup
- T005, T006, and T007 can run in parallel during Foundational
- User stories can proceed in parallel after the Foundational phase if multiple developers are available
- T009 and T010 are parallel within User Story 1 because they address independent service layers
- T015 and T019 are parallel because they operate in separate feature domains: UI and evaluation

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate the Q&A flow independently with a known PDF and question set
5. Only then proceed to User Story 2 or 3

### Incremental Delivery

1. Deliver the secure parsing and Q&A flow with citation verification
2. Add Streamlit citation navigation and user review workflow
3. Add evaluation benchmarking and response-quality measurement
4. Finalize polish, cost review, and evidence-check validation
