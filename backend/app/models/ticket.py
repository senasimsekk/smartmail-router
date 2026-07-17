from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    record_number = Column(String, nullable=False, unique=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)
    application_type = Column(String, nullable=False)
    assigned_department = Column(String, nullable=False)
    responsible_person = Column(String, nullable=True)
    priority = Column(String, nullable=False)
    status = Column(String, default="Yeni", nullable=False)
    sla_due_at = Column(DateTime, nullable=True)
    notes = Column(JSON, default=list)
    response_text = Column(Text, nullable=True)
    closure_reason = Column(Text, nullable=True)
    created_by = Column(String, default="system", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
