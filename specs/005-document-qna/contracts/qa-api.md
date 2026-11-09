# Q&A API Contract

## Purpose

Defines the question and answer exchange for the document Q&A workflow.

## Request

```json
{
  "doc_id": "string",
  "question": "string",
  "reference_material": "boolean",
  "page_context": [
    {
      "page_num": 1,
      "text": "string"
    }
  ]
}
```

## Response

```json
{
  "answer_id": "string",
  "doc_id": "string",
  "question_id": "string",
  "text": "string",
  "citations": [
    {
      "page_num": 1,
      "evidence_text": "string"
    }
  ],
  "status": "verified"
}
```

## Rules

- The answer must include page citations in the final response.
- The response is rejected unless all cited pages are verified against source text.
- The interface must allow a citation label to jump to the matching page in the document.
