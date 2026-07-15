import secrets
import uuid

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from backend.models.referral import ReferralAttribution, ReferralLink, ReferralVisit


def create_or_get_referral(db: DBSession, owner_id: str) -> ReferralLink:
    link = db.query(ReferralLink).filter(ReferralLink.owner_user_id == owner_id).first()
    if link:
        return link
    link = ReferralLink(
        id=f"rl_{uuid.uuid4().hex}",
        owner_user_id=owner_id,
        code=secrets.token_urlsafe(9),
    )
    db.add(link)
    try:
        db.flush()
        return link
    except IntegrityError:
        db.rollback()
        return db.query(ReferralLink).filter(ReferralLink.owner_user_id == owner_id).one()


def record_referral_visit(db: DBSession, code: str) -> str | None:
    link = db.query(ReferralLink).filter(ReferralLink.code == code).first()
    if not link:
        return None
    visit = ReferralVisit(id=f"rv_{uuid.uuid4().hex}", referral_id=link.id)
    db.add(visit)
    db.flush()
    return visit.id


def attribute_registration(db: DBSession, visit_id: str | None, invitee_id: str) -> bool:
    if not visit_id:
        return False
    existing = db.query(ReferralAttribution).filter(ReferralAttribution.invitee_user_id == invitee_id).first()
    if existing:
        return False
    visit = db.query(ReferralVisit).filter(ReferralVisit.id == visit_id).first()
    if not visit:
        return False
    link = db.query(ReferralLink).filter(ReferralLink.id == visit.referral_id).first()
    if not link:
        return False
    if link.owner_user_id == invitee_id:
        raise ValueError("不能归因自己的分享链接")
    db.add(ReferralAttribution(
        id=f"ra_{uuid.uuid4().hex}",
        inviter_user_id=link.owner_user_id,
        invitee_user_id=invitee_id,
        visit_id=visit.id,
    ))
    db.flush()
    return True


def mark_first_learning_milestone(db: DBSession, user_id: str, kind: str) -> bool:
    column_by_kind = {
        "first_question": ReferralAttribution.first_question_at,
        "first_tutor_completed": ReferralAttribution.first_tutor_completed_at,
    }
    column = column_by_kind.get(kind)
    if column is None:
        raise ValueError("未知学习里程碑")
    attribution = db.query(ReferralAttribution).filter(ReferralAttribution.invitee_user_id == user_id).first()
    if not attribution or getattr(attribution, column.key) is not None:
        return False
    setattr(attribution, column.key, func.now())
    db.flush()
    return True


def owner_stats(db: DBSession, owner_id: str) -> dict[str, int]:
    return {
        "visits": db.query(ReferralVisit).join(ReferralLink).filter(ReferralLink.owner_user_id == owner_id).count(),
        "registrations": db.query(ReferralAttribution).filter(ReferralAttribution.inviter_user_id == owner_id).count(),
        "first_questions": db.query(ReferralAttribution).filter(
            ReferralAttribution.inviter_user_id == owner_id,
            ReferralAttribution.first_question_at.is_not(None),
        ).count(),
        "first_tutors": db.query(ReferralAttribution).filter(
            ReferralAttribution.inviter_user_id == owner_id,
            ReferralAttribution.first_tutor_completed_at.is_not(None),
        ).count(),
    }
