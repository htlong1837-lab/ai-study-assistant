# Quickstart: Document Q&A validation

## Prerequisites

- Python 3.11+
- PDF source document already passed through the secure intake path
- Access to the configured LLM provider and any required API credentials
- Streamlit installed in the development environment

## Validation scenarios

### 1. Parse a PDF into a structured document

1. Provide a test PDF to the parser.
2. Run the page extraction utility.
3. Confirm the output is a `ParsedDocument` with ordered pages and page numbers preserved.

Expected outcome: Each page has a numeric identifier and non-empty extracted text when the source page contains readable content.

### 2. Ask a grounded question and receive a verified answer

1. Load a PDF into the system.
2. Submit a question about the document content.
3. Review the answer and citation list.

Expected outcome: The answer contains explicit page references and each citation maps to an actual page in the document.

### 3. Reject unsupported citations

1. Trigger a prompt that could encourage unsupported page references.
2. Run the answer generation and verification flow.

Expected outcome: The answer is rejected and regeneration is required when citations do not match the source text.

### 4. Use the Streamlit interface

1. Launch the Streamlit app.
2. Upload or select a secure document.
3. Submit a question and click a citation label.

Expected outcome: The relevant page is surfaced or navigated in the document view.

### 5. Run evaluation with 30 benchmark questions

1. Load the benchmark question set.
2. Execute the evaluation run in both modes: with and without reference materials.
3. Compare citation accuracy and answer quality.

Expected outcome: Results show citation validity and the effect of reference materials on answer quality.
