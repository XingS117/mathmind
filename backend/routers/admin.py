import uuid, logging
from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from backend.database import get_db
from backend.models.user import User
from backend.models.operations import AdminAuditEvent, LoginEvent, RuntimeEvent
from backend.services.auth_service import hash_password, get_user_id
from fastapi import Request

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])

class CreateUserRequest(BaseModel):
    username: str
    password: str
    name: str
    school_level: str = "高中"


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


class ResetPasswordRequest(BaseModel):
    new_password: str

def require_admin(request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request)
    user = db.query(User).filter(User.id == uid).first()
    if not user or user.role != "admin" or not user.is_active:
        raise HTTPException(403, "仅管理员可操作")
    return user

@router.get("/admin/users")
def list_users(request: Request, db: DBSession = Depends(get_db)):
    require_admin(request, db)
    users = db.query(User).all()
    return {"users": [{"id": u.id, "username": u.username, "name": u.name, "role": u.role, "school_level": u.school_level, "created_at": str(u.created_at)} for u in users]}

@router.post("/admin/users")
def create_user(req: CreateUserRequest, request: Request, db: DBSession = Depends(get_db)):
    admin = require_admin(request, db)
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(400, "用户名已存在")
    if len(req.password) < 6:
        raise HTTPException(400, "密码至少6位")
    uid = f"u_{uuid.uuid4().hex[:12]}"
    user = User(id=uid, username=req.username, password_hash=hash_password(req.password), name=req.name, role="user", school_level=req.school_level)
    db.add(user)
    _audit(db, admin.id, user.id, "create_user")
    db.commit()
    logger.info(f"Created user {req.username} ({uid})")
    return {"id": uid, "username": req.username, "name": req.name}

@router.delete("/admin/users/{user_id}")
def delete_user(user_id: str, request: Request, db: DBSession = Depends(get_db)):
    admin = require_admin(request, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.role == "admin":
        raise HTTPException(400, "不能删除管理员")
    _audit(db, admin.id, user.id, "delete_user")
    db.delete(user)
    db.commit()
    return {"message": "用户已删除"}


def _audit(db: DBSession, admin_user_id: str, target_user_id: str, action: str) -> None:
    db.add(AdminAuditEvent(
        id=f"ae_{uuid.uuid4().hex}", admin_user_id=admin_user_id,
        target_user_id=target_user_id, action=action,
    ))


@router.patch("/admin/users/{user_id}/status")
def update_user_status(user_id: str, req: UpdateUserStatusRequest, request: Request, db: DBSession = Depends(get_db)):
    admin = require_admin(request, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.id == admin.id and not req.is_active:
        raise HTTPException(400, "不能停用自己的账户")
    user.is_active = req.is_active
    _audit(db, admin.id, user.id, "enable_user" if req.is_active else "disable_user")
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.post("/admin/users/{user_id}/reset-password")
def reset_password(user_id: str, req: ResetPasswordRequest, request: Request, db: DBSession = Depends(get_db)):
    admin = require_admin(request, db)
    if not 8 <= len(req.new_password) <= 128:
        raise HTTPException(400, "密码长度需为 8-128 位")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    user.password_hash = hash_password(req.new_password)
    _audit(db, admin.id, user.id, "reset_password")
    db.commit()
    return {"message": "密码已重置"}


@router.get("/admin/accounts-overview")
def accounts_overview(request: Request, db: DBSession = Depends(get_db)):
    require_admin(request, db)
    login_stats = (
        db.query(
            LoginEvent.user_id.label("user_id"), func.count(LoginEvent.id).label("login_count"),
            func.max(LoginEvent.occurred_at).label("last_login_at"),
        )
        .filter(LoginEvent.outcome == "success")
        .group_by(LoginEvent.user_id)
        .subquery()
    )
    rows = (
        db.query(User, login_stats.c.login_count, login_stats.c.last_login_at, LoginEvent.ip_masked, LoginEvent.user_agent_family)
        .outerjoin(login_stats, login_stats.c.user_id == User.id)
        .outerjoin(LoginEvent, (LoginEvent.user_id == User.id) & (LoginEvent.outcome == "success") & (LoginEvent.occurred_at == login_stats.c.last_login_at))
        .order_by(User.created_at.desc())
        .all()
    )
    return {"accounts": [{
        "id": user.id, "username": user.username, "name": user.name,
        "is_active": user.is_active, "created_at": str(user.created_at) if user.created_at else None,
        "login_count": login_count or 0,
        "last_login_at": str(last_login_at) if last_login_at else None,
        "last_ip_masked": ip_masked, "user_agent_family": user_agent_family,
    } for user, login_count, last_login_at, ip_masked, user_agent_family in rows]}


@router.get("/admin/runtime-overview")
def runtime_overview(request: Request, db: DBSession = Depends(get_db)):
    require_admin(request, db)
    rows = (
        db.query(
            RuntimeEvent.feature, RuntimeEvent.engine_kind, RuntimeEvent.provider,
            RuntimeEvent.model_name, RuntimeEvent.outcome,
            func.count(RuntimeEvent.id).label("count"),
            func.avg(RuntimeEvent.duration_ms).label("avg_duration_ms"),
        )
        .group_by(RuntimeEvent.feature, RuntimeEvent.engine_kind, RuntimeEvent.provider, RuntimeEvent.model_name, RuntimeEvent.outcome)
        .order_by(RuntimeEvent.feature, RuntimeEvent.engine_kind, RuntimeEvent.provider, RuntimeEvent.model_name, RuntimeEvent.outcome)
        .all()
    )
    return {"events": [{
        "feature": row.feature, "engine_kind": row.engine_kind, "provider": row.provider,
        "model_name": row.model_name, "outcome": row.outcome, "count": row.count,
        "avg_duration_ms": round(row.avg_duration_ms) if row.avg_duration_ms is not None else None,
    } for row in rows]}
