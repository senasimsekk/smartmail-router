from app.models.feedback import Feedback


def create_feedback(
    db,
    email_id: int,
    original_classification: dict,
    corrected_category: str,
    corrected_department: str,
    corrected_priority: str,
    feedback_note: str | None = None,
    created_by: str | None = None,
) -> Feedback:
    is_misdirected = (
        original_classification["category"] != corrected_category
        or original_classification["department"] != corrected_department
        or original_classification["priority"] != corrected_priority
    )

    feedback = Feedback(
        email_id=email_id,
        original_category=original_classification["category"],
        original_department=original_classification["department"],
        original_priority=original_classification["priority"],
        corrected_category=corrected_category,
        corrected_department=corrected_department,
        corrected_priority=corrected_priority,
        is_misdirected=is_misdirected,
        feedback_note=feedback_note,
        created_by=created_by,
    )

    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return feedback


def get_feedbacks_by_email_id(db, email_id: int) -> list[Feedback]:
    return (
        db.query(Feedback)
        .filter(Feedback.email_id == email_id)
        .order_by(Feedback.created_at.desc())
        .all()
    )


def get_all_feedbacks(db) -> list[Feedback]:
    return (
        db.query(Feedback)
        .order_by(Feedback.created_at.desc())
        .all()
    )


def feedback_to_dict(feedback: Feedback) -> dict:
    return {
        "id": feedback.id,
        "email_id": feedback.email_id,
        "original_category": feedback.original_category,
        "original_department": feedback.original_department,
        "original_priority": feedback.original_priority,
        "corrected_category": feedback.corrected_category,
        "corrected_department": feedback.corrected_department,
        "corrected_priority": feedback.corrected_priority,
        "is_misdirected": feedback.is_misdirected,
        "feedback_note": feedback.feedback_note,
        "created_by": feedback.created_by,
        "created_at": feedback.created_at,
    }


def create_training_example_from_feedback(feedback: Feedback, email: dict) -> dict:
    return {
        "email_id": feedback.email_id,
        "subject": email["subject"],
        "body": email["body"],
        "sender": email["sender"],
        "source_mailbox": email.get("source_mailbox"),
        "original_label": {
            "category": feedback.original_category,
            "department": feedback.original_department,
            "priority": feedback.original_priority,
        },
        "corrected_label": {
            "category": feedback.corrected_category,
            "department": feedback.corrected_department,
            "priority": feedback.corrected_priority,
        },
        "feedback_note": feedback.feedback_note,
    }