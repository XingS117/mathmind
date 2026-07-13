import json, logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func
from backend.database import get_db
from backend.models.question import Question
from backend.models.session import Session
from backend.models.mastery import Mastery
from backend.models.review import ReviewSchedule
from backend.schemas.api_schemas import DashboardData
from backend.services.auth_service import get_user_id
from backend.services.knowmap_service import get_node

logger = logging.getLogger(__name__)
router = APIRouter(tags=["learn"])

GENERIC_DIAGNOSTIC_POINTS = {"本题关键步骤", "思路启动"}

def _parse_json(val, fallback=None):
    if fallback is None:
        fallback = []
    if val is None:
        return fallback
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return fallback
    return fallback

def _question_graph_labels(question: Question | None, node_lookup=get_node) -> list[str]:
    if not question:
        return []
    labels: list[str] = []
    for node_id in _parse_json(question.knowmap_nodes, []):
        node = node_lookup(node_id)
        if node and node.get("name"):
            labels.append(node["name"])
    if labels:
        return labels
    return _parse_json(question.knowledge_points, [])

def _recent_diagnostic_weak_points(
    sessions: list[Session],
    q_map: dict[str, Question] | None = None,
    node_lookup=get_node,
    limit: int = 5,
) -> list[str]:
    points: list[str] = []
    seen: set[str] = set()
    for s in sessions:
        raw = getattr(s, "diagnostic_json", None)
        if not raw:
            continue
        try:
            diagnostic = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            continue
        spots = diagnostic.get("weak_spots", []) or []
        question_id = getattr(s, "question_id", None)
        if question_id and any(spot in GENERIC_DIAGNOSTIC_POINTS for spot in spots):
            spots = _question_graph_labels((q_map or {}).get(question_id), node_lookup) or spots
        for spot in spots:
            if spot and spot not in seen:
                seen.add(spot)
                points.append(spot)
            if len(points) >= limit:
                return points
    return points

@router.get("/learn/dashboard", response_model=DashboardData)
def dashboard(request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request, db=db)
    q_count = db.query(Question).filter(Question.user_id == uid).count()
    s_count = db.query(Session).filter(Session.user_id == uid).count()
    avg = db.query(func.avg(Mastery.score)).filter(Mastery.user_id == uid).scalar() or 0

    weak = db.query(Mastery).filter(
        Mastery.user_id == uid, Mastery.score < 0.4
    ).order_by(Mastery.score).limit(5).all()
    mastery_weak_points = [m.node_id for m in weak]

    recent = db.query(Session).filter(
        Session.user_id == uid
    ).order_by(Session.last_active.desc()).limit(5).all()
    sessions = db.query(Session).filter(Session.user_id == uid).all()
    questions = db.query(Question).filter(Question.id.in_([s.question_id for s in sessions])).all() if sessions else []
    q_map = {q.id: q for q in questions}
    diagnostic_weak_points = _recent_diagnostic_weak_points(recent, q_map=q_map, limit=5)
    weak_points = diagnostic_weak_points or mastery_weak_points

    # Session distribution by knowledge point
    node_counts: dict = {}
    for s in sessions:
        q = q_map.get(s.question_id)
        if q and q.knowledge_points:
            kps = json.loads(q.knowledge_points) if isinstance(q.knowledge_points, str) else q.knowledge_points
            for kp in (kps or [])[:2]:
                node_counts[kp] = node_counts.get(kp, 0) + 1
    top_studied = sorted(node_counts.items(), key=lambda x: -x[1])[:6]
    now = datetime.utcnow()
    due_reviews = db.query(ReviewSchedule).filter(
        ReviewSchedule.user_id == uid,
        ReviewSchedule.completed == False,
        ReviewSchedule.scheduled_date <= now,
    ).order_by(ReviewSchedule.scheduled_date).limit(3).all()
    mastery_change = db.query(func.sum(Mastery.score)).filter(
        Mastery.user_id == uid,
        Mastery.last_reviewed >= now - timedelta(days=7),
    ).scalar() or 0

    return DashboardData(
        total_questions=q_count, total_sessions=s_count,
        avg_mastery=round(float(avg), 2), weak_points=weak_points,
        recent_sessions=[{"id": s.id, "status": s.status} for s in recent],
        top_studied=[{"node": k, "count": v} for k, v in top_studied],
        due_reviews=[{
            "id": review.id,
            "question_id": review.question_id,
            "round": review.review_round,
            "type": review.review_type,
            "scheduled_date": str(review.scheduled_date)[:10],
        } for review in due_reviews],
        mastery_change=round(float(mastery_change), 2),
    )

@router.get("/learn/progress")
def progress(request: Request, db: DBSession = Depends(get_db)):
    records = db.query(Mastery).filter(Mastery.user_id == get_user_id(request, db=db)).all()
    return {"mastery": [{"node_id": m.node_id, "score": m.score} for m in records]}

@router.get("/learn/history")
def history(request: Request, db: DBSession = Depends(get_db)):
    sessions = db.query(Session).filter(
        Session.user_id == get_user_id(request, db=db)
    ).order_by(Session.last_active.desc()).limit(20).all()
    return {"sessions": [
        {"id": s.id, "question_id": s.question_id, "status": s.status,
         "steps": f"{s.current_step}/{s.total_steps}",
         "last_active": str(s.last_active)} for s in sessions
    ]}
