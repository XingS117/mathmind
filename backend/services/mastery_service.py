import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session as DBSession

from backend.models.mastery import Mastery
from backend.models.question import Question
from backend.models.review import ReviewSchedule
from backend.models.session import Session


REVIEW_DELTAS = {1: 0.05, 2: 0.10, 3: 0.15, 4: 0.20}


@dataclass
class MasteryUpdate:
    updated_nodes: list[str]


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


def _apply_delta(db: DBSession, user_id: str, nodes: list[str], delta: float) -> None:
    for node_id in nodes:
        mastery = db.query(Mastery).filter(
            Mastery.user_id == user_id,
            Mastery.node_id == node_id,
        ).first()
        if not mastery:
            mastery = Mastery(
                id=f"m_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                node_id=node_id,
                score=0.0,
                total_sessions=0,
                correct_sessions=0,
            )
            db.add(mastery)
        mastery.score = min(1.0, max(0.0, float(mastery.score or 0.0) + delta))
        mastery.total_sessions = int(mastery.total_sessions or 0) + 1
        if delta > 0:
            mastery.correct_sessions = int(mastery.correct_sessions or 0) + 1
        mastery.last_reviewed = _utcnow()


def apply_tutor_mastery(
    db: DBSession,
    user_id: str,
    question: Question,
    session: Session,
    delta: float,
) -> MasteryUpdate:
    """Apply one completed tutor session exactly once."""
    if session.mastery_applied_at:
        return MasteryUpdate(updated_nodes=[])
    nodes = canonical_question_nodes(question)
    _apply_delta(db, user_id, nodes, delta)
    session.mastery_applied_at = _utcnow()
    return MasteryUpdate(updated_nodes=nodes)


def apply_review_mastery(db: DBSession, review: ReviewSchedule) -> MasteryUpdate:
    """Apply a completed review's fixed round delta exactly once."""
    if review.mastery_applied_at:
        return MasteryUpdate(updated_nodes=[])
    question = db.query(Question).filter(
        Question.id == review.question_id,
        Question.user_id == review.user_id,
    ).first()
    nodes = canonical_question_nodes(question) if question else []
    _apply_delta(db, review.user_id, nodes, REVIEW_DELTAS.get(review.review_round, 0.0))
    review.mastery_applied_at = _utcnow()
    return MasteryUpdate(updated_nodes=nodes)
