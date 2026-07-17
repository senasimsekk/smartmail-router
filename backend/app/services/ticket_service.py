from datetime import datetime

from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.services.classification_service import classify_email
from app.services.email_db_service import email_to_dict
from app.services.sla_service import calculate_sla, parse_created_at
from app.services.system_log_service import create_system_log


TICKET_STATUSES = [
    "Yeni",
    "Sınıflandırıldı",
    "Onay bekliyor",
    "Birimine yönlendirildi",
    "İşlemde",
    "Cevap bekleniyor",
    "Tamamlandı",
    "Arşivlendi",
    "Hatalı yönlendirme",
]


DEPARTMENT_RESPONSIBLES = {
    "Bilgi İşlem": "Bilgi İşlem Uzmanı",
    "Hukuk Müşavirliği": "Hukuk Müşaviri",
    "Basın ve Halkla İlişkiler": "Basın Sorumlusu",
    "Satın Alma": "Satın Alma Sorumlusu",
    "Evrak Kayıt": "Evrak Kayıt Memuru",
    "İlgili Uzman Daire": "Uzman Daire Sorumlusu",
    "Strateji / Mali İşler": "Mali İşler Sorumlusu",
    "İnsan Kaynakları": "İK Sorumlusu",
}


def ticket_to_dict(ticket: Ticket) -> dict:
    return {
        "id": ticket.id,
        "record_number": ticket.record_number,
        "email_id": ticket.email_id,
        "application_type": ticket.application_type,
        "assigned_department": ticket.assigned_department,
        "responsible_person": ticket.responsible_person,
        "priority": ticket.priority,
        "status": ticket.status,
        "sla_due_at": ticket.sla_due_at.isoformat() if ticket.sla_due_at else None,
        "notes": ticket.notes or [],
        "response_text": ticket.response_text,
        "closure_reason": ticket.closure_reason,
        "created_by": ticket.created_by,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }


def build_record_number(email_id: int, created_at: datetime | None = None) -> str:
    record_date = created_at or datetime.utcnow()
    return f"RK-{record_date.year}-{email_id:06d}"


def derive_ticket_status(email: dict, classification: dict) -> str:
    routing_status = email.get("routing_status")

    if routing_status == "Corrected":
        return "Hatalı yönlendirme"

    if routing_status == "Pending Review" or classification.get("requires_human_review"):
        return "Onay bekliyor"

    if routing_status in {"Routed", "Approved"}:
        return "Birimine yönlendirildi"

    if routing_status == "Archived":
        return "Arşivlendi"

    if routing_status == "Completed":
        return "Tamamlandı"

    if routing_status == "Classified":
        return "Sınıflandırıldı"

    return "Yeni"


def get_ticket_by_email_id(db: Session, email_id: int) -> Ticket | None:
    return db.query(Ticket).filter(Ticket.email_id == email_id).first()


def create_or_update_ticket_for_email(
    db: Session,
    email_record,
    created_by: str = "system",
) -> dict:
    email = email_to_dict(email_record)
    classification = classify_email(email)
    sla = calculate_sla(email, classification)
    status = derive_ticket_status(email, classification)
    assigned_department = (
        email.get("approved_department")
        or classification.get("department")
        or "Evrak Kayıt"
    )
    ticket = get_ticket_by_email_id(db, email_record.id)

    if ticket is None:
        ticket = Ticket(
            record_number=build_record_number(
                email_id=email_record.id,
                created_at=parse_created_at(email.get("created_at")),
            ),
            email_id=email_record.id,
            application_type=classification.get("category") or "Genel Başvuru",
            assigned_department=assigned_department,
            responsible_person=DEPARTMENT_RESPONSIBLES.get(assigned_department),
            priority=classification.get("priority") or "Normal",
            status=status,
            sla_due_at=parse_created_at(sla["due_at"]),
            notes=[],
            created_by=created_by,
        )
        db.add(ticket)
    else:
        ticket.application_type = classification.get("category") or ticket.application_type
        ticket.assigned_department = assigned_department
        ticket.responsible_person = (
            ticket.responsible_person
            or DEPARTMENT_RESPONSIBLES.get(assigned_department)
        )
        ticket.priority = classification.get("priority") or ticket.priority
        ticket.status = status
        ticket.sla_due_at = parse_created_at(sla["due_at"])

    db.commit()
    db.refresh(ticket)

    create_system_log(
        db=db,
        email_id=email_record.id,
        action_type="TICKET_CREATED",
        action_detail="Ticket record was created or updated for the email.",
        actor=created_by,
        extra_data={
            "record_number": ticket.record_number,
            "status": ticket.status,
            "assigned_department": ticket.assigned_department,
        },
    )

    return ticket_to_dict(ticket)


def update_ticket(
    db: Session,
    ticket_id: int,
    status: str | None = None,
    responsible_person: str | None = None,
    note: str | None = None,
    response_text: str | None = None,
    closure_reason: str | None = None,
    actor: str = "operator",
) -> dict | None:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if ticket is None:
        return None

    if status:
        if status not in TICKET_STATUSES:
            raise ValueError(f"Unsupported ticket status: {status}")
        ticket.status = status

    if responsible_person is not None:
        ticket.responsible_person = responsible_person

    if response_text is not None:
        ticket.response_text = response_text

    if closure_reason is not None:
        ticket.closure_reason = closure_reason

    if note:
        notes = list(ticket.notes or [])
        notes.append(
            {
                "text": note,
                "created_by": actor,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        ticket.notes = notes

    db.commit()
    db.refresh(ticket)

    create_system_log(
        db=db,
        email_id=ticket.email_id,
        action_type="TICKET_UPDATED",
        action_detail="Ticket record was updated.",
        actor=actor,
        extra_data={
            "record_number": ticket.record_number,
            "status": ticket.status,
        },
    )

    return ticket_to_dict(ticket)
