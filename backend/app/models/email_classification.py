from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text

from app.database import Base


class EmailClassification(Base):
    __tablename__ = "email_classifications"

    id = Column(Integer, primary_key=True, index=True)

    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)

    category = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    priority = Column(String(50), nullable=False)
    requires_human_review = Column(Boolean, default=False)

    matched_keywords = Column(JSON, default=list)
    confidence_score = Column(Float, nullable=False)
    explanation = Column(Text, nullable=True)

    category_correct = Column(Boolean, nullable=True)
    department_correct = Column(Boolean, nullable=True)
    priority_correct = Column(Boolean, nullable=True)
    requires_human_review_correct = Column(Boolean, nullable=True)
    all_correct = Column(Boolean, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)