# Data Model: Document Q&A via API

## Core entities

### Document

Represents the source document that has passed the secure intake boundary.

Fields:
- `doc_id`: unique document identifier
- `file_path`: secure path to the source PDF or slide deck
- `source_email_id`: optional identifier for the originating email or intake source
- `pages`: ordered list of page objects
- `metadata`: optional source information retained for traceability

Validation rules:
- `doc_id` must be present and immutable after intake.
- `file_path` must resolve to a valid source artifact.
- `pages` must remain in order and correspond to the original file.

### Page

Represents one page of the source document.

Fields:
- `page_num`: one-based page number
- `text`: extracted text for the page
- `source_hash`: optional checksum for integrity validation

Validation rules:
- `page_num` must be positive and unique within a document.
- `text` may be empty only when the page is intentionally blank or non-textual; a citation must never reference an empty source page.

### Question

Represents a user prompt tied to a document.

Fields:
- `question_id`: unique identifier for the request
- `doc_id`: target document reference
- `text`: raw user question
- `reference_mode`: whether the system is operating with or without reference material

Validation rules:
- `doc_id` must reference an existing document.
- `text` must be non-empty before dispatch to the LLM.

### Answer

Represents the final answer returned to the user after verification.

Fields:
- `answer_id`: unique identifier
- `doc_id`: source document
- `question_id`: associated question
- `text`: answer text
- `citations`: list of citation objects
- `status`: draft, verified, or rejected

Validation rules:
- `status` must be `verified` before presentation to the user.
- `citations` must match the source pages and include valid page numbers.

### Citation

Represents a source-backed page reference.

Fields:
- `page_num`: page number invoked in the answer
- `evidence_text`: quoted or summarized source phrase supporting the claim
- `confidence`: confidence judgment from verification logic

Validation rules:
- `page_num` must exist in the document.
- `evidence_text` must match or be substantiated by the extracted page text.
- If evidence is insufficient, the answer is rejected rather than surfaced.

### EvaluationRun

Represents a benchmark test set for citation quality measurement.

Fields:
- `run_id`: unique identifier
- `question_set`: collection of benchmark questions
- `with_reference_material`: boolean
- `results`: per-question outcome records

Validation rules:
- A run must record answer quality and citation validity.
- Results must allow comparison between reference and non-reference modes.

## Relationships

- One `Document` contains many `Page` records.
- One `Question` pertains to one `Document` and yields one `Answer`.
- One `Answer` includes many `Citation` records.
- One `EvaluationRun` contains many benchmark `Question` outcomes.

## State transitions

- `Document` moves from intake → parsed → verified.
- `Answer` moves from draft → verified → displayed or rejected.
- `EvaluationRun` moves from created → executed → summarized.
