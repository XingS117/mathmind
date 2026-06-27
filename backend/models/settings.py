from sqlalchemy import Column, String, DateTime, func
from backend.database import Base

class UserSettings(Base):
    __tablename__ = "user_settings"
    user_id = Column(String, primary_key=True)
    model_provider = Column(String, default="mock")
    model_name = Column(String, default="mock")
    api_key = Column(String, default="")
    base_url = Column(String, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())