from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from app.database import Base

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)

    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    sender = Column(String, nullable=False)
    source_mailbox= Column(String, nullable=False)
    requires_human_review = Column(Boolean, default=False)
    has_attachment= Column(Boolean, default=False)
    attachment_names = Column(JSON, default=list)
    attachment_texts = Column(JSON, default=list)

    expected_category = Column(String, nullable=True)
    expected_department = Column(String, nullable=True)
    expected_priority = Column(String, nullable=True)   
    requires_human_review= Column(Boolean, default=False)
    routing_status= Column (String, default="New")
    approved_department= Column(String, nullable=True)
    approved_by= Column(String, nullable=True)
    approved_at= Column(DateTime, nullable=True)
    routing_note= Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
