from sqlalchemy import Column, String, Integer, Boolean, DateTime, func
from backend.database import Base

class ReviewSchedule(Base):
    __tablename__ = "review_schedule"
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    question_id = Column(String, nullable=False)
    review_round = Column(Integer, default=1)
    review_type = Column(String, default="quick")
    scheduled_date = Column(DateTime)
    completed = Column(Boolean, default=False)
    completed_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())