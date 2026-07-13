from sqlalchemy import Column, DateTime, Integer, String, func

from backend.database import Base


class LoginEvent(Base):
    __tablename__ = "login_events"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True, index=True)
    occurred_at = Column(DateTime, server_default=func.now(), index=True)
    outcome = Column(String, nullable=False)
    ip_masked = Column(String, nullable=False)
    ip_fingerprint = Column(String, nullable=False, index=True)
    user_agent_family = Column(String, default="unknown")


class RuntimeEvent(Base):
    __tablename__ = "runtime_events"

    id = Column(String, primary_key=True)
    occurred_at = Column(DateTime, server_default=func.now(), index=True)
    feature = Column(String, nullable=False)
    engine_kind = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    model_name = Column(String, default="")
    outcome = Column(String, nullable=False)
    duration_ms = Column(Integer, nullable=True)
    error_code = Column(String, nullable=True)


class AdminAuditEvent(Base):
    __tablename__ = "admin_audit_events"

    id = Column(String, primary_key=True)
    admin_user_id = Column(String, nullable=False, index=True)
    target_user_id = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False)
    occurred_at = Column(DateTime, server_default=func.now(), index=True)
