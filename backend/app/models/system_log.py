from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from app.database import Base



class SystemLog(Base):

    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
 
    email_id = Column(
        Integer,
        ForeignKey("emails.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    action_type = Column(String(100), nullable=False)
    action_detail = Column(Text, nullable=True)

    actor= Column(String(100), default="System")
    status = Column(String(50), default="Success")

    extra_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
