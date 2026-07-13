import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session as DBSession
from backend.database import get_db
from backend.models.user import User
from backend.services.auth_service import hash_password, verify_password, needs_password_upgrade, create_token, get_user_id
from backend.services.operations_service import client_ip, record_login_event
from backend.services.rate_limit_service import rate_limiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str

    @validator("username")
    def username_is_valid(cls, value):
        if not re.fullmatch(r"[A-Za-z0-9_-]{3,32}", value):
            raise ValueError("用户名需为 3-32 位字母、数字、下划线或连字符")
        return value

    @validator("password")
    def password_is_valid(cls, value):
        if not 8 <= len(value) <= 128:
            raise ValueError("密码长度需为 8-128 位")
        return value

    @validator("name")
    def name_is_valid(cls, value):
        value = value.strip()
        if not 1 <= len(value) <= 32:
            raise ValueError("显示名长度需为 1-32 位")
        return value


class UpdateProfileRequest(BaseModel):
    name: str

    @validator("name")
    def name_is_valid(cls, value):
        value = value.strip()
        if not 1 <= len(value) <= 32:
            raise ValueError("显示名长度需为 1-32 位")
        return value

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, request: Request, db: DBSession = Depends(get_db)):
    if not rate_limiter.allow(client_ip(request), "register", limit=10):
        raise HTTPException(429, "注册请求过于频繁，请稍后再试")
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(409, "用户名已存在")
    user = User(
        id=f"u_{uuid.uuid4().hex}", username=req.username, password_hash=hash_password(req.password),
        name=req.name, role="user", school_level="高中", is_active=True,
    )
    db.add(user)
    db.commit()
    return {"user": {"id": user.id, "name": user.name, "role": user.role, "school_level": user.school_level}}


@router.post("/auth/login")
def login(req: LoginRequest, request: Request, db: DBSession = Depends(get_db)):
    if not rate_limiter.allow(client_ip(request), "login", limit=5):
        record_login_event(db, request, "rate_limited")
        raise HTTPException(429, "登录请求过于频繁，请稍后再试")
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not user.password_hash:
        record_login_event(db, request, "failed")
        raise HTTPException(401, "用户名或密码错误")
    if not verify_password(req.password, user.password_hash):
        record_login_event(db, request, "failed", user.id)
        raise HTTPException(401, "用户名或密码错误")
    if not user.is_active:
        record_login_event(db, request, "disabled", user.id)
        raise HTTPException(403, "账户已停用")
    if needs_password_upgrade(user.password_hash):
        user.password_hash = hash_password(req.password)
        db.commit()
    record_login_event(db, request, "success", user.id)
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


@router.put("/auth/profile")
def update_profile(req: UpdateProfileRequest, request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request)
    if uid == "u_default":
        raise HTTPException(401, "请先登录")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    user.name = req.name
    db.commit()
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
