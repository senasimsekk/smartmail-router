from app.models.email import Email


def email_to_dict(email: Email) -> dict:
   

    return {
        "id": email.id,
        "subject": email.subject,
        "sender": email.sender,
        "body": email.body,
        "source_mailbox": email.source_mailbox,
        "has_attachment": email.has_attachment,
        "attachment_names": email.attachment_names or [],
        "attachment_texts": email.attachment_texts or [],
        "expected_category": email.expected_category,
        "expected_department": email.expected_department,
        "expected_priority": email.expected_priority,
        "requires_human_review": email.requires_human_review,
        "routing_status": email.routing_status,
        "approved_department": email.approved_department,
        "approved_by": email.approved_by,
        "approved_at": email.approved_at.isoformat() if email.approved_at else None,
        "routing_note": email.routing_note,
        "created_at": email.created_at.isoformat() if email.created_at else None,
    }


def get_all_emails_from_db(db) -> list[Email]:
    """
    Database'deki tüm e-postaları id sırasına göre getirir.
    """

    return db.query(Email).order_by(Email.id).all()


def get_email_by_id_from_db(db, email_id: int) -> Email | None:
    """
    Database'den id'ye göre tek bir e-posta getirir.
    Bulamazsa None döndürür.
    """

    return db.query(Email).filter(Email.id == email_id).first()
from sqlalchemy import func

SUPPORTED_EMAIL_SOURCES = [
    "IMAP / SMTP",
    "Microsoft Exchange",
    "Outlook / Microsoft 365",
    "Gmail",
    "Kurumsal mail sunucusu",
    "Ortak posta kutuları",
    "Birim posta kutuları",
    "API ile mail aktarımı",
    "E-posta arşivinden toplu aktarım",
]


def get_mailbox_statistics(db) -> list[dict]:
    mailbox_counts = (
        db.query(
            Email.source_mailbox,
            func.count(Email.id),
        )
        .group_by(Email.source_mailbox)
        .order_by(Email.source_mailbox)
        .all()
    )

    statistics = []

    for source_mailbox, email_count in mailbox_counts:
        statistics.append(
            {
                "mailbox": source_mailbox or "unknown",
                "email_count": email_count,
            }
        )

    return statistics


def get_emails_by_source_mailbox(db, mailbox: str) -> list[dict]:
    email_records = (
        db.query(Email)
        .filter(Email.source_mailbox == mailbox)
        .order_by(Email.id)
        .all()
    )

    return [email_to_dict(email) for email in email_records]


def get_email_ingestion_overview(db) -> dict:
    mailbox_statistics = get_mailbox_statistics(db)

    total_email_count = sum(
        mailbox["email_count"]
        for mailbox in mailbox_statistics
    )

    return {
        "module_name": "E-posta Alma Modülü",
        "mode": "Synthetic MVP",
        "description": (
            "Bu MVP sürümünde gerçek mail sunucusuna bağlanmak yerine, "
            "sentetik e-posta verileri farklı posta kutularından gelmiş gibi işlenir."
        ),
        "supported_sources": SUPPORTED_EMAIL_SOURCES,
        "mailbox_statistics": mailbox_statistics,
        "total_email_count": total_email_count,
    }
