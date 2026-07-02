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

    expected_category = Column(String, nullable=True)
    expected_department = Column(String, nullable=True)
    expected_priority = Column(String, nullable=True)   
    requires_human_review= Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)