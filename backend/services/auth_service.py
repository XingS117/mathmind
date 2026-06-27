import os, uuid, hashlib, secrets
from datetime import datetime, timedelta
import jwt
from fastapi import Request

JWT_SECRET = os.getenv("JWT_SECRET", "mathmind-dev-secret-key-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 90

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${h}"

def verify_password(password: str, hashed: str) -> bool:
    if not hashed or "$" not in hashed:
        return False
    parts = hashed.split("$", 1)
    salt, h = parts[0], parts[1]
    return hashlib.sha256((salt + password).encode()).hexdigest() == h

def create_token(user_id: str) -> str:
    expiry = datetime.utcnow() + timedelta(days=JWT_EXPIRY_DAYS)
    payload = {"sub": user_id, "exp": expiry, "iat": datetime.utcnow()}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except:
        return None

def get_user_id(request, default: str = "u_default") -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_token(auth[7:])
        if payload:
            return payload.get("sub", default)
    return default