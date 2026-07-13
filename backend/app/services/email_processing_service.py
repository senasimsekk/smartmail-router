from sqlalchemy.orm import Session

from app.models.email import Email
from app.services.classification_service import classify_email
from app.services.classification_db_service import save_classification_result
from app.services.email_db_service import email_to_dict
from app.services.evaluation_service import evaluate_classification


def process_email_by_id(db: Session, email_id: int) -> dict | None:
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        return None

    email_dict = email_to_dict(email)

    classification_result = classify_email(email_dict)

    evaluation_result = evaluate_classification(
        email=email_dict,
        classification=classification_result,
    )

    saved_classification = save_classification_result(
        db=db,
        email_id=email.id,
        classification=classification_result,
        evaluation_result=evaluation_result,
    )

    requires_human_review = classification_result.get(
        "requires_human_review",
        False,
    )

    email.requires_human_review = requires_human_review

    if requires_human_review:
        email.routing_status = "Pending Review"
    else:
        email.routing_status = "Classified"

    db.commit()
    db.refresh(email)

    return {
        "message": "Email was processed successfully.",
        "email": email_to_dict(email),
        "classification": classification_result,
        "evaluation": evaluation_result,
        "saved_classification": saved_classification,
    }