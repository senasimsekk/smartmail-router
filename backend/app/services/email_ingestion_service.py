import json
from pathlib import Path

from sqlalchemy.orm import Session  

from app.models.email import Email  
from app.services.email_db_service import email_to_dict
from app.services.email_processing_service import process_email_by_id
from app.services.system_log_service import create_system_log


PROJECT_DIR = Path(__file__).resolve().parents[3]
SYNTHETIC_EMAILS_FILE = PROJECT_DIR / "data" / "synthetic_emails.json"


def load_synthetic_mailbox_emails() -> list[dict]:
    if not SYNTHETIC_EMAILS_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {SYNTHETIC_EMAILS_FILE}")

    with open(SYNTHETIC_EMAILS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def normalize_attachment_names(attachment_names: list[str] | None) -> list[str]:
    if attachment_names is None:
        return []

    return [
        attachment_name.strip()
        for attachment_name in attachment_names
        if attachment_name and attachment_name.strip()
    ]


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


def sync_synthetic_mailbox(
    db: Session,
    source_mailbox: str = "webmaster@rekabet.gov.tr",
    limit: int = 5,
    process_after_import: bool = True,
) -> dict:
    synthetic_emails = load_synthetic_mailbox_emails()
    mailbox_candidates = [
        email_data
        for email_data in synthetic_emails
        if email_data.get("source_mailbox") == source_mailbox
    ]

    imported_emails = []
    processed_results = []
    skipped_duplicates = 0

    for email_data in mailbox_candidates:
        if len(imported_emails) >= limit:
            break

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
        action_detail="Synthetic mailbox was synchronized.",
        actor="mailbox_sync",
        extra_data={
            "source_mailbox": source_mailbox,
            "limit": limit,
            "imported_count": len(imported_emails),
            "skipped_duplicate_count": skipped_duplicates,
            "candidate_count": len(mailbox_candidates),
        },
    )

    return {
        "message": "Synthetic mailbox synchronized successfully.",
        "source_mailbox": source_mailbox,
        "candidate_count": len(mailbox_candidates),
        "imported_count": len(imported_emails),
        "skipped_duplicate_count": skipped_duplicates,
        "imported_emails": imported_emails,
        "processing_results": processed_results,
    }
