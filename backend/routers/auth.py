import uuid, logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from backend.database import get_db
from backend.models.user import User
from backend.services.auth_service import hash_password, verify_password, create_token, decode_token, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/auth/login")
def login(req: LoginRequest, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not user.password_hash:
        raise HTTPException(401, "用户名或密码错误")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "name": user.name, "role": user.role, "school_level": user.school_level}}

@router.get("/auth/me")
def get_me(request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request)
    if uid == "u_default":
        return {"id": "u_default", "name": "游客", "role": "user", "school_level": "高中"}
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        return {"id": "u_default", "name": "游客", "role": "user", "school_level": "高中"}
    return {"id": user.id, "name": user.name, "role": user.role, "school_level": user.school_level}

@router.put("/auth/password")
def change_password(req: ChangePasswordRequest, request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request)
    if uid == "u_default":
        raise HTTPException(401, "请先登录")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(400, "旧密码错误")
    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"message": "密码已修改"}