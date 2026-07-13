import uuid, logging, json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession
from backend.database import get_db
from backend.models.session import Session
from backend.models.question import Question
from backend.schemas.api_schemas import (
    TutorSessionCreate, TutorSessionResponse,
    TutorMessageRequest, TutorMessageResponse
)
from backend.services.tutor_engine import process_message
from backend.services.mastery_service import apply_tutor_mastery
from backend.routers.review import schedule_reviews
from backend.services.auth_service import get_user_id

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tutor"])

def _parse_json(val):
    if val is None: return []
    if isinstance(val, (list, dict)): return val
    if isinstance(val, str):
        try: return json.loads(val)
        except: return []
    return []

@router.post("/tutor/session", response_model=TutorSessionResponse)
def create_session(req: TutorSessionCreate, request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request, db=db)
    question = db.query(Question).filter(
        Question.id == req.question_id,
        Question.user_id == uid,
    ).first()
    if not question:
        raise HTTPException(404, "Question not found")
    session_id = f"s_{uuid.uuid4().hex[:12]}"
    teaching = question.teaching_json
    if isinstance(teaching, str):
        teaching = json.loads(teaching) if teaching else {}
    steps = teaching.get("teachable_steps", []) if teaching else []

    db_session = Session(
        id=session_id, user_id=uid, question_id=req.question_id,
        total_steps=len(steps), current_step=0,
        steps_json=json.dumps([{"step": s["step_number"], "status": "pending", "attempts": 0} for s in steps]),
        messages_json=json.dumps([]), hints_used=0, mistakes_json=json.dumps([])
    )
    db.add(db_session)
    db.commit()

    opening = steps[0]["guiding_question"] if steps else "这道题怎么做？"
    diagram_json = None
    if question.has_diagram and question.diagram_json:
        try: diagram_json = json.loads(question.diagram_json) if isinstance(question.diagram_json, str) else question.diagram_json
        except: pass

    solution_confidence = str(teaching.get("solution_confidence") or "unknown") if teaching else "unknown"
    uncertain_points = list(teaching.get("uncertain_points") or []) if teaching else []

    return TutorSessionResponse(
        session_id=session_id, question_text=question.text or "",
        opening=opening, total_steps=len(steps), hints_available=3,
        has_diagram=bool(question.has_diagram), diagram_json=diagram_json,
        solution_confidence=solution_confidence,
        uncertain_points=uncertain_points,
    )

@router.post("/tutor/message", response_model=TutorMessageResponse)
def tutor_message(req: TutorMessageRequest, request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request, db=db)
    db_session = db.query(Session).filter(
        Session.id == req.session_id,
        Session.user_id == uid,
    ).first()
    if not db_session:
        raise HTTPException(404, "Session not found")
    question = db.query(Question).filter(
        Question.id == db_session.question_id,
        Question.user_id == uid,
    ).first()
    if not question:
        raise HTTPException(404, "Question not found")
    teaching = question.teaching_json if question else None
    if isinstance(teaching, str):
        teaching = json.loads(teaching) if teaching else {}
    steps = teaching.get("teachable_steps", []) if teaching else []
    was_in_progress = db_session.status == "in_progress"
    result = process_message(db_session, req.message, req.intent, steps, db)

    # If session completed, find variants (related questions)
    if was_in_progress and db_session.status == "completed" and not db_session.mastery_applied_at:
        apply_tutor_mastery(db, uid, question, db_session, result.get("mastery_update") or 0.0)
        schedule_reviews(uid, question.id, db)
        result["reviews_scheduled"] = True
        nodes = _parse_json(question.knowmap_nodes)
        if nodes:
            related = db.query(Question).filter(
                Question.id != question.id,
                Question.user_id == uid,
                Question.status == "complete"
            ).limit(3).all()
            result["variants"] = [q.id for q in related]
    else:
        db.commit()
        if result.get("type") == "complete":
            result["reviews_scheduled"] = False

    return TutorMessageResponse(**result)

@router.get("/tutor/sessions/active")
def get_active_session(request: Request, db: DBSession = Depends(get_db)):
    s = db.query(Session).filter(
        Session.user_id == get_user_id(request, db=db), Session.status == "in_progress"
    ).order_by(Session.last_active.desc()).first()
    if not s: return {"session_id": None}
    return {"session_id": s.id, "question_id": s.question_id}

@router.get("/tutor/sessions/{session_id}")
def get_session(session_id: str, request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request, db=db)
    s = db.query(Session).filter(Session.id == session_id, Session.user_id == uid).first()
    if not s: raise HTTPException(404, "Session not found")
    return {"id": s.id, "question_id": s.question_id, "status": s.status,
        "current_step": s.current_step, "total_steps": s.total_steps}
