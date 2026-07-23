from sqlalchemy.orm import Session  

from app.models.email import Email  
from app.services.email_db_service import email_to_dict
from app.services.email_processing_service import process_email_by_id
from app.services.mail_connector_service import (
    SYNTHETIC_EMAILS_FILE,
    build_connector,
)
from app.services.system_log_service import create_system_log


def load_synthetic_mailbox_emails() -> list[dict]:
    if not SYNTHETIC_EMAILS_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {SYNTHETIC_EMAILS_FILE}")

    return build_connector("synthetic_demo", "webmaster@rekabet.gov.tr").load_messages()


def normalize_attachment_names(attachment_names: list[str] | None) -> list[str]:
    if attachment_names is None:
        return []

    return [
        attachment_name.strip()
        for attachment_name in attachment_names
        if attachment_name and attachment_name.strip()
    ]


SYSTEM_NOTIFICATION_SENDERS = {
    "no-reply@accounts.google.com",
    "mail-noreply@google.com",
    "noreply@google.com",
}

SYSTEM_NOTIFICATION_SUBJECTS = [
    "security alert",
    "2-step verification",
    "critical security alert",
    "google account",
]


def should_ignore_connector_message(email_data: dict) -> bool:
    sender = (email_data.get("sender") or "").lower().strip()
    subject = (email_data.get("subject") or "").lower().strip()

    if sender in SYSTEM_NOTIFICATION_SENDERS:
        return True

    return any(keyword in subject for keyword in SYSTEM_NOTIFICATION_SUBJECTS)


def email_already_exists(
    db: Session,
    subject: str,
    sender: str,
    source_mailbox: str,
) -> bool:
    return (
        db.query(Email)
        .filter(
            Email.subject == subject,
            Email.sender == sender,
            Email.source_mailbox == source_mailbox,
        )
        .first()
        is not None
    )

def create_email_from_manual_import(
        db: Session,
        subject: str,
        sender: str,
        body: str,
        source_mailbox: str = "webmaster@rekabet.gov.tr",
        has_attachment: bool = False,
        attachment_names: list[str] | None = None,
        attachment_texts: list[dict] | None = None,
        expected_category: str | None = None,
        expected_department: str | None = None,
        expected_priority: str | None = None,
        requires_human_review: bool = False,
        actor: str = "manual_import",
) ->dict:
    attachment_names = normalize_attachment_names(attachment_names)

    new_email = Email(
        subject=subject,
        sender=sender,
        body=body,
        source_mailbox=source_mailbox,
        has_attachment=has_attachment,
        attachment_names=attachment_names,
        attachment_texts=attachment_texts or [],
        expected_category=expected_category,
        expected_department=expected_department,
        expected_priority=expected_priority,
        requires_human_review=requires_human_review,
        routing_status="New",
    )

    db.add(new_email)
    db.commit()
    db.refresh(new_email)
    create_system_log(
        db=db,
        email_id=new_email.id,
        action_type="EMAIL_IMPORTED",
        action_detail="Email was manually imported into the system.",
        actor=actor,
        extra_data={
            "source_mailbox": source_mailbox,
            "has_attachment": has_attachment,
            "attachment_names": attachment_names,
        },
    )
    return email_to_dict(new_email)


def sync_mailbox_from_connector(
    db: Session,
    connector_id: str = "synthetic_demo",
    source_mailbox: str = "webmaster@rekabet.gov.tr",
    limit: int = 5,
    process_after_import: bool = True,
) -> dict:
    connector = build_connector(connector_id, source_mailbox)
    mailbox_candidates = connector.fetch_messages(limit=limit)

    imported_emails = []
    processed_results = []
    skipped_duplicates = 0
    skipped_ignored = 0

    for email_data in mailbox_candidates:
        if len(imported_emails) >= limit:
            break

        if should_ignore_connector_message(email_data):
            skipped_ignored += 1
            continue

        if email_already_exists(
            db=db,
            subject=email_data["subject"],
            sender=email_data["sender"],
            source_mailbox=email_data.get("source_mailbox", source_mailbox),
        ):
            skipped_duplicates += 1
            continue

        imported_email = create_email_from_manual_import(
            db=db,
            subject=email_data["subject"],
            sender=email_data["sender"],
            body=email_data["body"],
            source_mailbox=email_data.get("source_mailbox", source_mailbox),
            has_attachment=email_data.get("has_attachment", False),
            attachment_names=email_data.get("attachment_names", []),
            attachment_texts=email_data.get("attachment_texts", []),
            expected_category=email_data.get("expected_category"),
            expected_department=email_data.get("expected_department"),
            expected_priority=email_data.get("expected_priority"),
            requires_human_review=email_data.get("requires_human_review", False),
            actor="mailbox_sync",
        )
        imported_emails.append(imported_email)

        if process_after_import:
            processed_result = process_email_by_id(
                db=db,
                email_id=imported_email["id"],
            )
            processed_results.append(processed_result)

    create_system_log(
        db=db,
        action_type="MAILBOX_SYNCED",
        action_detail="Mailbox connector was synchronized.",
        actor="mailbox_sync",
        extra_data={
            "connector_id": connector.config.connector_id,
            "connector_name": connector.config.name,
            "source_mailbox": source_mailbox,
            "limit": limit,
            "imported_count": len(imported_emails),
            "skipped_duplicate_count": skipped_duplicates,
            "skipped_ignored_count": skipped_ignored,
            "candidate_count": len(mailbox_candidates),
        },
    )

    return {
        "message": "Mailbox synchronized successfully.",
        "connector": {
            "connector_id": connector.config.connector_id,
            "name": connector.config.name,
            "source_type": connector.config.source_type,
            "mode": connector.config.mode,
            "status": connector.config.status,
        },
        "source_mailbox": source_mailbox,
        "candidate_count": len(mailbox_candidates),
        "imported_count": len(imported_emails),
        "skipped_duplicate_count": skipped_duplicates,
        "skipped_ignored_count": skipped_ignored,
        "imported_emails": imported_emails,
        "processing_results": processed_results,
    }


def sync_synthetic_mailbox(
    db: Session,
    source_mailbox: str = "webmaster@rekabet.gov.tr",
    limit: int = 5,
    process_after_import: bool = True,
) -> dict:
    return sync_mailbox_from_connector(
        db=db,
        connector_id="synthetic_demo",
        source_mailbox=source_mailbox,
        limit=limit,
        process_after_import=process_after_import,
    )
