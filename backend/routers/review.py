import uuid, logging, json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from backend.database import get_db
from backend.models.review import ReviewSchedule
from backend.models.question import Question
from backend.services.auth_service import get_user_id
from backend.services.mastery_service import apply_review_mastery
from fastapi import Request

logger = logging.getLogger(__name__)
router = APIRouter(tags=["review"])

REVIEW_INTERVALS = [10, 30, 90, 180]
REVIEW_TYPES = ["quick", "variant", "comprehensive", "final"]

@router.get("/learn/reviews")
def get_reviews(request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request, db=db)
    now = datetime.utcnow()
    upcoming = db.query(ReviewSchedule).filter(
        ReviewSchedule.user_id == uid,
        ReviewSchedule.completed == False,
        ReviewSchedule.scheduled_date <= now
    ).order_by(ReviewSchedule.scheduled_date).all()
    future = db.query(ReviewSchedule).filter(
        ReviewSchedule.user_id == uid,
        ReviewSchedule.completed == False,
        ReviewSchedule.scheduled_date > now
    ).order_by(ReviewSchedule.scheduled_date).limit(10).all()
    return {
        "upcoming": [{"id": r.id, "question_id": r.question_id, "round": r.review_round, "type": r.review_type, "scheduled_date": str(r.scheduled_date)[:10]} for r in upcoming],
        "future": [{"id": r.id, "question_id": r.question_id, "round": r.review_round, "type": r.review_type, "scheduled_date": str(r.scheduled_date)[:10]} for r in future]
    }

@router.post("/learn/reviews/{review_id}/complete")
def complete_review(review_id: str, request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request, db=db)
    review = db.query(ReviewSchedule).filter(
        ReviewSchedule.id == review_id,
        ReviewSchedule.user_id == uid,
    ).first()
    if not review:
        raise HTTPException(404, "Review not found")
    if not review.completed:
        review.completed = True
        review.completed_date = datetime.utcnow()
        apply_review_mastery(db, review)
    db.commit()
    return {"status": "ok", "message": "Review completed"}

def schedule_reviews(user_id: str, question_id: str, db: DBSession):
    for i in range(4):
        rid = f"rev_{uuid.uuid4().hex[:12]}"
        scheduled = datetime.utcnow() + timedelta(days=REVIEW_INTERVALS[i])
        r = ReviewSchedule(id=rid, user_id=user_id, question_id=question_id,
            review_round=i+1, review_type=REVIEW_TYPES[i], scheduled_date=scheduled)
        db.add(r)
    db.commit()
    return True
