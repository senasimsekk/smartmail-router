from collections import Counter

from sqlalchemy.orm import Session

from app.models.email import Email
from app.models.system_log import SystemLog
from app.services.classification_service import classify_email
from app.services.email_db_service import email_to_dict
from app.services.sla_service import calculate_sla
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

    sla_status_distribution = Counter()

    for email_record in emails:
        email = email_to_dict(email_record)
        classification = classify_email(email)
        sla = calculate_sla(email, classification)
        sla_status_distribution[sla["status_label"]] += 1

    sla_due_soon_count = sla_status_distribution.get("Yaklaşıyor", 0)
    sla_overdue_count = sla_status_distribution.get("Gecikti", 0)

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
        "sla_due_soon_count": sla_due_soon_count,
        "sla_overdue_count": sla_overdue_count,
        "routing_status_distribution": dict(routing_status_distribution),
        "sla_status_distribution": dict(sla_status_distribution),
        "system_log_action_distribution": dict(system_log_action_distribution),
        "latest_logs": [system_log_to_dict(log) for log in latest_logs],
    }
