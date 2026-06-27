import uuid, logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from backend.database import get_db
from backend.models.user import User
from backend.services.auth_service import hash_password, get_user_id
from fastapi import Request

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])

class CreateUserRequest(BaseModel):
    username: str
    password: str
    name: str
    school_level: str = "高中"

def require_admin(request: Request, db: DBSession = Depends(get_db)):
    uid = get_user_id(request)
    user = db.query(User).filter(User.id == uid).first()
    if not user or user.role != "admin":
        raise HTTPException(403, "仅管理员可操作")
    return user

@router.get("/admin/users")
def list_users(request: Request, db: DBSession = Depends(get_db)):
    require_admin(request, db)
    users = db.query(User).all()
    return {"users": [{"id": u.id, "username": u.username, "name": u.name, "role": u.role, "school_level": u.school_level, "created_at": str(u.created_at)} for u in users]}

@router.post("/admin/users")
def create_user(req: CreateUserRequest, request: Request, db: DBSession = Depends(get_db)):
    require_admin(request, db)
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(400, "用户名已存在")
    if len(req.password) < 6:
        raise HTTPException(400, "密码至少6位")
    uid = f"u_{uuid.uuid4().hex[:12]}"
    user = User(id=uid, username=req.username, password_hash=hash_password(req.password), name=req.name, role="user", school_level=req.school_level)
    db.add(user)
    db.commit()
    logger.info(f"Created user {req.username} ({uid})")
    return {"id": uid, "username": req.username, "name": req.name}

@router.delete("/admin/users/{user_id}")
def delete_user(user_id: str, request: Request, db: DBSession = Depends(get_db)):
    require_admin(request, db)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.role == "admin":
        raise HTTPException(400, "不能删除管理员")
    db.delete(user)
    db.commit()
    return {"message": "用户已删除"}