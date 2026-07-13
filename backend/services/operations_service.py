import hashlib
import os
import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from backend.models.operations import LoginEvent


_IP_FINGERPRINT_SECRET = os.getenv("IP_FINGERPRINT_SECRET", "mathmind-ip-fingerprint")


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def mask_ip(ip: str) -> str:
    if "." in ip:
        parts = ip.split(".")
        if len(parts) == 4:
            return ".".join(parts[:3] + ["*"])
    if ":" in ip:
        parts = ip.split(":")
        return ":".join(parts[:3] + ["*"])
    return "unknown"


def fingerprint_ip(ip: str) -> str:
    return hashlib.sha256(f"{_IP_FINGERPRINT_SECRET}:{ip}".encode()).hexdigest()


def user_agent_family(user_agent: str) -> str:
    value = (user_agent or "").lower()
    if "edg/" in value:
        return "Edge"
    if "firefox/" in value:
        return "Firefox"
    if "chrome/" in value or "chromium/" in value:
        return "Chrome"
    if "safari/" in value:
        return "Safari"
    if "curl/" in value:
        return "curl"
    return "unknown"


def record_login_event(db: Session, request: Request, outcome: str, user_id: str | None = None) -> None:
    ip = client_ip(request)
    db.add(LoginEvent(
        id=f"le_{uuid.uuid4().hex}",
        user_id=user_id,
        outcome=outcome,
        ip_masked=mask_ip(ip),
        ip_fingerprint=fingerprint_ip(ip),
        user_agent_family=user_agent_family(request.headers.get("user-agent", "")),
    ))
    db.commit()
