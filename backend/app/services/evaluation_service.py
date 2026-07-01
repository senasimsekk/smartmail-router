def evaluate_classification(email: dict, classification: dict) -> dict:
    """
    Sınıflandırma sonucunu veri setindeki beklenen sonuçla karşılaştırır.
    """

    expected_result = {
        "category": email.get("expected_category"),
        "department": email.get("expected_department"),
        "priority": email.get("expected_priority"),
        "requires_human_review": email.get("requires_human_review"),
    }

    evaluation = {
        "category_correct": classification["category"] == expected_result["category"],
        "department_correct": classification["department"] == expected_result["department"],
        "priority_correct": classification["priority"] == expected_result["priority"],
        "requires_human_review_correct": classification["requires_human_review"] == expected_result["requires_human_review"],
    }

    all_correct = all(evaluation.values())

    return {
        "expected_result": expected_result,
        "evaluation": evaluation,
        "all_correct": all_correct,
    }