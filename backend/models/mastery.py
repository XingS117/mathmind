from sqlalchemy import Column, String, Float, Integer, Boolean, JSON, DateTime, UniqueConstraint, func
from backend.database import Base

class Mastery(Base):
    __tablename__ = "mastery"
    __table_args__ = (UniqueConstraint("user_id", "node_id", name="uq_mastery_user_node"),)
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    node_id = Column(String, nullable=False)
    score = Column(Float, default=0.0)
    total_sessions = Column(Integer, default=0)
    correct_sessions = Column(Integer, default=0)
    variant_passed = Column(Boolean, default=False)
    last_reviewed = Column(DateTime)
    manual_adjustments = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
