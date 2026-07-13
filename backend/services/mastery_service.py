import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import case, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from backend.models.mastery import Mastery
from backend.models.mastery_change_event import MasteryChangeEvent
from backend.models.question import Question
from backend.models.review import ReviewSchedule
from backend.models.session import Session


REVIEW_DELTAS = {1: 0.05, 2: 0.10, 3: 0.15, 4: 0.20}


@dataclass
class MasteryUpdate:
    updated_nodes: list[str]
    applied: bool = False


def _utcnow() -> datetime:
    """Return a SQLite-compatible UTC timestamp."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def canonical_question_nodes(question: Question) -> list[str]:
    """Return the question's explicit knowmap nodes, or its knowledge points."""
    nodes = _canonicalize(_as_list(question.knowmap_nodes))
    return nodes or _canonicalize(_as_list(question.knowledge_points))


def _canonicalize(source: list) -> list[str]:
    nodes: list[str] = []
    for node in source:
        normalized = str(node or "").strip()
        if normalized and normalized not in nodes:
            nodes.append(normalized)
    return nodes


def _apply_delta(db: DBSession, user_id: str, nodes: list[str], delta: float, source: str) -> None:
    for node_id in nodes:
        try:
            with db.begin_nested():
                db.add(Mastery(
                    id=f"m_{uuid.uuid4().hex[:12]}",
                    user_id=user_id,
                    node_id=node_id,
                    score=0.0,
                    total_sessions=0,
                    correct_sessions=0,
                ))
                db.flush()
        except IntegrityError:
            pass
        db.execute(
            update(Mastery).where(
                Mastery.user_id == user_id,
                Mastery.node_id == node_id,
            ).values(
                score=func.min(1.0, func.max(0.0, Mastery.score + delta)),
                total_sessions=Mastery.total_sessions + 1,
                correct_sessions=case(
                    (delta > 0, Mastery.correct_sessions + 1),
                    else_=Mastery.correct_sessions,
                ),
                last_reviewed=_utcnow(),
            )
        )
        db.add(MasteryChangeEvent(
            id=f"mce_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            node_id=node_id,
            delta=delta,
            source=source,
            occurred_at=_utcnow(),
        ))


def apply_tutor_mastery(
    db: DBSession,
    user_id: str,
    question: Question,
    session: Session,
    delta: float,
) -> MasteryUpdate:
    """Apply one completed tutor session exactly once."""
    claimed = db.execute(
        update(Session).where(
            Session.id == session.id,
            Session.user_id == user_id,
            Session.status == "completed",
            Session.mastery_applied_at.is_(None),
        ).values(mastery_applied_at=_utcnow())
    )
    if claimed.rowcount != 1:
        return MasteryUpdate(updated_nodes=[])
    nodes = canonical_question_nodes(question)
    _apply_delta(db, user_id, nodes, delta, source="tutor")
    return MasteryUpdate(updated_nodes=nodes, applied=True)


def apply_review_mastery(db: DBSession, review: ReviewSchedule) -> MasteryUpdate:
    """Apply a completed review's fixed round delta exactly once."""
    claimed = db.execute(
        update(ReviewSchedule).where(
            ReviewSchedule.id == review.id,
            ReviewSchedule.user_id == review.user_id,
            ReviewSchedule.mastery_applied_at.is_(None),
        ).values(mastery_applied_at=_utcnow())
    )
    if claimed.rowcount != 1:
        return MasteryUpdate(updated_nodes=[])
    question = db.query(Question).filter(
        Question.id == review.question_id,
        Question.user_id == review.user_id,
    ).first()
    nodes = canonical_question_nodes(question) if question else []
    _apply_delta(
        db, review.user_id, nodes,
        REVIEW_DELTAS.get(review.review_round, 0.0),
        source="review",
    )
    return MasteryUpdate(updated_nodes=nodes, applied=True)
