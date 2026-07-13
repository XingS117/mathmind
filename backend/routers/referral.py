from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession

from backend.database import get_db
from backend.services.auth_service import get_user_id
from backend.services.operations_service import client_ip, fingerprint_ip
from backend.services.referral_service import create_or_get_referral, owner_stats, record_referral_visit
from backend.services.rate_limit_service import rate_limiter

router = APIRouter(tags=["referrals"])


@router.post("/referrals/visit/{code}", status_code=status.HTTP_201_CREATED)
def record_visit(code: str, request: Request, db: DBSession = Depends(get_db)):
    visitor_key = f"{fingerprint_ip(client_ip(request))}:{code}"
    if not rate_limiter.allow(visitor_key, "referral_visit", limit=20, window_seconds=3600):
        raise HTTPException(429, "访问分享链接过于频繁，请稍后再试")
    visit_id = record_referral_visit(db, code)
    if visit_id is None:
        raise HTTPException(404, "分享链接不存在")
    db.commit()
    return {"visit_id": visit_id}


@router.get("/referrals/me")
def my_referral(request: Request, db: DBSession = Depends(get_db)):
    owner_id = get_user_id(request, db=db)
    if owner_id == "u_default":
        raise HTTPException(401, "请先登录")
    link = create_or_get_referral(db, owner_id)
    db.commit()
    payload = owner_stats(db, owner_id)
    base_url = str(request.base_url).rstrip("/")
    return {"code": link.code, "share_url": f"{base_url}/?ref={link.code}", **payload}
