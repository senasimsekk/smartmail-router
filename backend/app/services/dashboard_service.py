from collections import Counter

from sqlalchemy.orm import Session

from app.models.email import Email
from app.models.system_log import SystemLog
from app.services.system_log_service import system_log_to_dict


def get_operational_dashboard_summary(db: Session) -> dict:
    emails = db.query(Email).all()
    logs = db.query(SystemLog).all()

    total_emails = len(emails)

    routing_status_distribution = Counter(
        email.routing_status or "Unknown" for email in emails
    )

    system_log_action_distribution = Counter(
        log.action_type for log in logs
    )

    pending_review_count = sum(
        1 for email in emails if email.routing_status == "Pending Review"
    )

    approved_count = sum(
        1 for email in emails if email.routing_status == "Approved"
    )

    corrected_count = sum(
        1 for email in emails if email.routing_status == "Corrected"
    )

    classified_count = sum(
        1 for email in emails if email.routing_status == "Classified"
    )

    human_review_count = sum(
        1 for email in emails if email.requires_human_review
    )

    attachment_email_count = sum(
        1 for email in emails if email.has_attachment
    )

    imported_email_count = system_log_action_distribution.get(
        "EMAIL_IMPORTED",
        0,
    )

    processed_email_count = system_log_action_distribution.get(
        "EMAIL_PROCESSED",
        0,
    )

    latest_logs = (
        db.query(SystemLog)
        .order_by(SystemLog.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "total_emails": total_emails,
        "imported_email_count": imported_email_count,
        "processed_email_count": processed_email_count,
        "pending_review_count": pending_review_count,
        "approved_count": approved_count,
        "corrected_count": corrected_count,
        "classified_count": classified_count,
        "human_review_count": human_review_count,
        "attachment_email_count": attachment_email_count,
        "routing_status_distribution": dict(routing_status_distribution),
        "system_log_action_distribution": dict(system_log_action_distribution),
        "latest_logs": [system_log_to_dict(log) for log in latest_logs],
    }