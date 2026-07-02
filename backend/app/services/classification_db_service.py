from app.models.email_classification import EmailClassification


def save_classification_result(
    db,
    email_id: int,
    classification: dict,
    evaluation_result: dict,
) -> EmailClassification:


    db.query(EmailClassification).filter(
        EmailClassification.email_id == email_id
    ).delete()

    evaluation = evaluation_result["evaluation"]

    classification_record = EmailClassification(
        email_id=email_id,
        category=classification["category"],
        department=classification["department"],
        priority=classification["priority"],
        requires_human_review=classification["requires_human_review"],
        matched_keywords=classification.get("matched_keywords", []),
        confidence_score=classification["confidence_score"],
        explanation=classification.get("explanation"),
        category_correct=evaluation["category_correct"],
        department_correct=evaluation["department_correct"],
        priority_correct=evaluation["priority_correct"],
        requires_human_review_correct=evaluation["requires_human_review_correct"],
        all_correct=evaluation_result["all_correct"],
    )

    db.add(classification_record)
    db.commit()
    db.refresh(classification_record)

    return classification_record


def classification_record_to_dict(record: EmailClassification) -> dict:
    """
    SQLAlchemy classification objesini JSON response için dictionary'e çevirir.
    """

    return {
        "id": record.id,
        "email_id": record.email_id,
        "category": record.category,
        "department": record.department,
        "priority": record.priority,
        "requires_human_review": record.requires_human_review,
        "matched_keywords": record.matched_keywords or [],
        "confidence_score": record.confidence_score,
        "explanation": record.explanation,
        "category_correct": record.category_correct,
        "department_correct": record.department_correct,
        "priority_correct": record.priority_correct,
        "requires_human_review_correct": record.requires_human_review_correct,
        "all_correct": record.all_correct,
        "created_at": record.created_at,
    }