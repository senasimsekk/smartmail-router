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
        "expected_category": email.expected_category,
        "expected_department": email.expected_department,
        "expected_priority": email.expected_priority,
        "requires_human_review": email.requires_human_review,
        "created_at": email.created_at,
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