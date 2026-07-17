from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.email import Email
from app.services.classification_service import classify_email
from app.services.classification_db_service import save_classification_result
from app.services.email_db_service import email_to_dict
from app.services.evaluation_service import evaluate_classification
from app.services.system_log_service import create_system_log
from app.services.ticket_service import create_or_update_ticket_for_email


AUTO_ROUTE_CONFIDENCE_THRESHOLD = 0.85


def determine_processing_routing_decision(classification_result: dict) -> dict:
    confidence_score = classification_result.get("confidence_score") or 0
    requires_human_review = classification_result.get("requires_human_review", False)

    if requires_human_review:
        return {
            "routing_status": "Pending Review",
            "auto_route": False,
            "reason": "İnsan onayı zorunlu.",
        }

    if confidence_score >= AUTO_ROUTE_CONFIDENCE_THRESHOLD:
        return {
            "routing_status": "Routed",
            "auto_route": True,
            "reason": "Güven skoru otomatik yönlendirme eşiğini geçti.",
        }

    return {
        "routing_status": "Pending Review",
        "auto_route": False,
        "reason": "Güven skoru operatör onayı gerektiriyor.",
    }


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

    routing_decision = determine_processing_routing_decision(classification_result)
    requires_human_review = (
        classification_result.get("requires_human_review", False)
        or routing_decision["routing_status"] == "Pending Review"
    )

    email.requires_human_review = requires_human_review
    email.routing_status = routing_decision["routing_status"]

    if routing_decision["auto_route"]:
        email.approved_department = classification_result.get("department")
        email.approved_by = "system"
        email.approved_at = datetime.utcnow()
        email.routing_note = routing_decision["reason"]

    db.commit()
    db.refresh(email)

    processing_log = create_system_log(
        db=db,
        email_id=email.id,
        action_type="EMAIL_PROCESSED",
        action_detail="Email was classified and processing status was updated.",
        actor="system",
        extra_data={
            "category": classification_result.get("category"),
            "department": classification_result.get("department"),
            "priority": classification_result.get("priority"),
            "confidence_score": classification_result.get("confidence_score"),
            "requires_human_review": requires_human_review,
            "routing_status": email.routing_status,
            "auto_route": routing_decision["auto_route"],
            "routing_reason": routing_decision["reason"],
        },
    )

    routing_log = None

    if routing_decision["auto_route"]:
        routing_log = create_system_log(
            db=db,
            email_id=email.id,
            action_type="EMAIL_ROUTED",
            action_detail="Email was automatically routed after classification.",
            actor="system",
            extra_data={
                "approved_department": email.approved_department,
                "confidence_score": classification_result.get("confidence_score"),
                "routing_reason": routing_decision["reason"],
            },
        )

    ticket = None
    ticket_error = None

    try:
        ticket = create_or_update_ticket_for_email(
            db=db,
            email_record=email,
            created_by="system",
        )
    except SQLAlchemyError as error:
        db.rollback()
        ticket_error = str(error)

    return {
        "message": "Email was processed successfully.",
        "email": email_to_dict(email),
        "classification": classification_result,
        "evaluation": evaluation_result,
        "saved_classification": saved_classification,
        "system_log": processing_log,
        "routing_log": routing_log,
        "routing_decision": routing_decision,
        "ticket": ticket,
        "ticket_error": ticket_error,
    }
