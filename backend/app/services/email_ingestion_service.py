from sqlalchemy.orm import Session  

from app.models.email import Email  
from app.services.email_db_service import email_to_dict

def create_email_from_manual_import(
        db: Session,
        subject: str,
        sender: str,
        body: str,
        source_mailbox: str = "webmaster@rekabet.gov.tr",
        has_attachment: bool = False,
        attachment_names: list[str] | None = None,
) ->dict:
    if attachment_names is None:
        attachment_names = []

    new_email = Email(
        subject=subject,
        sender=sender,
        body=body,
        source_mailbox=source_mailbox,
        has_attachment=has_attachment,
        attachment_names=attachment_names,
        expected_category=None,
        expected_department=None,
        expected_priority=None,
        requires_human_review=False,
        routing_status="New",
    )

    db.add(new_email)
    db.commit()
    db.refresh(new_email)
    return email_to_dict(new_email)