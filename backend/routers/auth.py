import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession
from backend.database import get_db
from backend.models.user import User
from backend.services.auth_service import hash_password, verify_password, needs_password_upgrade, create_token, get_user_id
from backend.services.password_policy import validate_password_length
from backend.services.username_policy import validate_registration_username
from backend.services.operations_service import client_ip, record_login_event
from backend.services.referral_service import attribute_registration
from backend.services.rate_limit_service import rate_limiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])
DUMMY_PASSWORD_HASH = hash_password("invalid-password-placeholder")


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str
    referral_visit_id: str | None = None

    @validator("username")
    def username_is_valid(cls, value):
        return validate_registration_username(value)

    @validator("password")
    def password_is_valid(cls, value):
        return validate_password_length(value)

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
    try:
        if req.referral_visit_id:
            attribute_registration(db, req.referral_visit_id, user.id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "用户名已存在")
    return {"user": {"id": user.id, "name": user.name, "role": user.role, "school_level": user.school_level}}


@router.get("/auth/username-availability")
def username_availability(
    request: Request,
    username: str,
    db: DBSession = Depends(get_db),
):
    try:
        validate_registration_username(username)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not rate_limiter.allow(client_ip(request), "username_availability", limit=60):
        raise HTTPException(429, "用户名检查过于频繁，请稍后再试")
    return {"available": db.query(User).filter(User.username == username).first() is None}


@router.post("/auth/login")
def login(req: LoginRequest, request: Request, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not user.password_hash:
        verify_password(req.password, DUMMY_PASSWORD_HASH)
        _reject_login(db, request, "failed")
    if not verify_password(req.password, user.password_hash):
        _reject_login(db, request, "failed", user.id)
    if not user.is_active:
        _reject_login(db, request, "disabled", user.id, status_code=403, detail="账户已停用")
    if needs_password_upgrade(user.password_hash):
        user.password_hash = hash_password(req.password)
        db.commit()
    record_login_event(db, request, "success", user.id)
    token = create_token(user.id)
    return {"token": token, "user": {"id": user.id, "name": user.name, "role": user.role, "school_level": user.school_level}}


def _reject_login(db: DBSession, request: Request, outcome: str, user_id: str | None = None,
                  status_code: int = 401, detail: str = "用户名或密码错误") -> None:
    if not rate_limiter.allow(client_ip(request), "login_failed", limit=5):
        record_login_event(db, request, "rate_limited", user_id)
        raise HTTPException(429, "登录请求过于频繁，请稍后再试")
    record_login_event(db, request, outcome, user_id)
    raise HTTPException(status_code, detail)

@router.get("/auth/me")
def get_me(request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request, db=db)
    if uid == "u_default":
        return {"id": "u_default", "name": "游客", "role": "user", "school_level": "高中"}
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        return {"id": "u_default", "name": "游客", "role": "user", "school_level": "高中"}
    return {"id": user.id, "name": user.name, "role": user.role, "school_level": user.school_level}


@router.put("/auth/profile")
def update_profile(req: UpdateProfileRequest, request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request, db=db)
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
    uid = get_user_id(request, db=db)
    if uid == "u_default":
        raise HTTPException(401, "请先登录")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    try:
        validate_password_length(req.new_password)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(400, "旧密码错误")
    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"message": "密码已修改"}
