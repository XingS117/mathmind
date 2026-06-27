from sqlalchemy import Column, String, Integer, Boolean, Text, JSON, DateTime, func
from backend.database import Base

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    question_id = Column(String, nullable=False)
    status = Column(String, default="in_progress")
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    steps_json = Column(JSON)
    messages_json = Column(JSON, default=list)
    hints_used = Column(Integer, default=0)
    mistakes_json = Column(JSON, default=list)
    diagnostic_json = Column(JSON, default=dict)
    mastery_achieved = Column(Boolean, default=False)
    variant_done = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    last_active = Column(DateTime, server_default=func.now(), onupdate=func.now())
