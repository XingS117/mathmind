from sqlalchemy import Column, DateTime, ForeignKey, String, func

from backend.database import Base


class ReferralLink(Base):
    __tablename__ = "referral_links"

    id = Column(String, primary_key=True)
    owner_user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class ReferralVisit(Base):
    __tablename__ = "referral_visits"

    id = Column(String, primary_key=True)
    referral_id = Column(String, ForeignKey("referral_links.id"), nullable=False, index=True)
    occurred_at = Column(DateTime, server_default=func.now(), nullable=False)


class ReferralAttribution(Base):
    __tablename__ = "referral_attributions"

    id = Column(String, primary_key=True)
    inviter_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    invitee_user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    visit_id = Column(String, ForeignKey("referral_visits.id"), unique=True, nullable=False)
    registered_at = Column(DateTime, server_default=func.now(), nullable=False)
    first_question_at = Column(DateTime, nullable=True)
    first_tutor_completed_at = Column(DateTime, nullable=True)
