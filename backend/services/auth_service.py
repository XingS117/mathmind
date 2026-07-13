import os, uuid, hashlib, hmac, secrets
from datetime import datetime, timedelta
import jwt
from fastapi import Request

JWT_SECRET = os.getenv("JWT_SECRET", "mathmind-dev-secret-key-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 90

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    if hashed.startswith("scrypt$"):
        parts = hashed.split("$")
        if len(parts) != 3:
            return False
        try:
            salt = bytes.fromhex(parts[1])
            expected = bytes.fromhex(parts[2])
            actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(actual, expected)
    if "$" not in hashed:
        return False
    salt, digest = hashed.split("$", 1)
    actual = hashlib.sha256((salt + password).encode()).hexdigest()
    return hmac.compare_digest(actual, digest)

def needs_password_upgrade(encoded: str) -> bool:
    return bool(encoded) and not encoded.startswith("scrypt$")

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
