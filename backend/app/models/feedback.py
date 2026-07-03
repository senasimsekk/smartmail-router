from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)

    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)

    original_category = Column(String(100), nullable=False)
    original_department = Column(String(100), nullable=False)
    original_priority = Column(String(50), nullable=False)

    corrected_category = Column(String(100), nullable=False)
    corrected_department = Column(String(100), nullable=False)
    corrected_priority = Column(String(50), nullable=False)

    is_misdirected = Column(Boolean, default=False)
    feedback_note = Column(Text, nullable=True)

    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)