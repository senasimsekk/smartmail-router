from datetime import datetime

from sqlalchemy.orm import Session

from app.models.email import Email
from app.services.classification_service import classify_email
from app.services.email_db_service import email_to_dict
from app.services.feedback_service import create_feedback, feedback_to_dict


def get_pending_review_emails(db: Session) -> list[dict]:
    emails = db.query(Email).all()

    pending_emails = []

    for email in emails:
        email_dict = email_to_dict(email)
        classification = classify_email(email_dict)

        needs_review = classification.get("requires_human_review", False)

        if needs_review or email.routing_status == "Pending Review":
            if email.routing_status == "New":
                email.routing_status = "Pending Review"

            pending_emails.append(
                {
                    "email": email_to_dict(email),
                    "classification": classification,
                }
            )

    db.commit()

    return pending_emails


def approve_email_routing(
    db: Session,
    email_id: int,
    approved_by: str,
    approved_department: str | None = None,
    routing_note: str | None = None,
) -> dict | None:
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        return None

    email_dict = email_to_dict(email)
    classification = classify_email(email_dict)

    final_department = approved_department or classification.get("department")

    email.routing_status = "Approved"
    email.approved_department = final_department
    email.approved_by = approved_by
    email.approved_at = datetime.utcnow()
    email.routing_note = routing_note

    db.commit()
    db.refresh(email)

    return {
        "message": "Email routing was approved successfully.",
        "email": email_to_dict(email),
        "classification": classification,
    }


def correct_email_routing(
    db: Session,
    email_id: int,
    corrected_category: str,
    corrected_department: str,
    corrected_priority: str,
    corrected_by: str,
    feedback_note: str | None = None,
) -> dict | None:
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        return None

    email_dict = email_to_dict(email)
    original_classification = classify_email(email_dict)

    feedback = create_feedback(
        db=db,
        email_id=email.id,
        original_classification=original_classification,
        corrected_category=corrected_category,
        corrected_department=corrected_department,
        corrected_priority=corrected_priority,
        feedback_note=feedback_note,
        created_by=corrected_by,
    )

    email.routing_status = "Corrected"
    email.approved_department = corrected_department
    email.approved_by = corrected_by
    email.approved_at = datetime.utcnow()
    email.routing_note = feedback_note

    db.commit()
    db.refresh(email)

    return {
        "message": "Email routing was corrected and feedback was saved.",
        "email": email_to_dict(email),
        "original_classification": original_classification,
        "feedback": feedback_to_dict(feedback),
    }