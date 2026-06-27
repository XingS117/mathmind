from sqlalchemy import Column, String, DateTime, func
from backend.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)
    name = Column(String, nullable=False)
    role = Column(String, default="user")
    school_level = Column(String, default="高中")
    created_at = Column(DateTime, server_default=func.now())