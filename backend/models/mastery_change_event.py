from sqlalchemy import Column, DateTime, Float, String, func

from backend.database import Base


class MasteryChangeEvent(Base):
    __tablename__ = "mastery_change_events"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    node_id = Column(String, nullable=False)
    delta = Column(Float, nullable=False)
    source = Column(String, nullable=False)
    occurred_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
