# Document Intake Contract

## Purpose

Defines the secure document payload accepted by Module A before PDF processing begins.

## Contract

```json
{
  "doc_id": "string",
  "file_path": "string",
  "source_email_id": "string|null",
  "document_type": "pdf"
}
```

## Rules

- `doc_id` must be unique within the secure intake scope.
- `file_path` must reference a valid source file.
- `source_email_id` is optional and preserved for traceability.
- `document_type` is restricted to PDF and supported slide deck documents only after security validation.

## Output

The pipeline must return a normalized `ParsedDocument` object containing `doc_id` and ordered pages with `page_num` and `text`.
