def build_instruction(
    action: str, custom_question: str = "", language: str = "Vietnamese"
) -> str:
    labels = {
        "explain": "Explain the selected passage clearly",
        "simplify": "Rewrite the selected passage in simpler language",
        "translate": f"Translate the selected passage into {language}",
        "define": "Explain key terms using the document; put general definitions in background_note",
    }
    if action == "custom":
        question = custom_question.strip()
        if not question or len(question) > 1000:
            raise ValueError("Câu hỏi cần có nội dung và không quá 1000 ký tự.")
        return question
    if action not in labels:
        raise ValueError("Thao tác không hợp lệ.")
    return labels[action]
