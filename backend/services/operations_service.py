import hashlib
import hmac
import os
import secrets
import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from backend.models.operations import LoginEvent, RuntimeEvent


# The random development fallback changes at process restart. Production deployment
# must configure MATHMIND_IP_HASH_SECRET when cross-restart correlation is required.
_IP_FINGERPRINT_SECRET = os.getenv("MATHMIND_IP_HASH_SECRET") or secrets.token_hex(32)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if os.getenv("MATHMIND_TRUST_PROXY") == "1" and forwarded:
        return forwarded.split(",", 1)[0].strip()
    host = request.client.host if request.client else "unknown"
    return "127.0.0.1" if host == "testclient" else host


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
    return hmac.new(_IP_FINGERPRINT_SECRET.encode(), ip.encode(), hashlib.sha256).hexdigest()


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


def record_runtime_event(
    db: Session,
    feature: str,
    engine_kind: str,
    provider: str,
    model_name: str,
    outcome: str,
    duration_ms: int | None,
    error_code: str | None = None,
) -> None:
    """Persist only approved operational metadata, never request content or secrets."""
    db.add(RuntimeEvent(
        id=f"re_{uuid.uuid4().hex}",
        feature=str(feature or "")[:64],
        engine_kind=str(engine_kind or "")[:32],
        provider=str(provider or "")[:64],
        model_name=str(model_name or "")[:128],
        outcome=str(outcome or "unknown")[:32],
        duration_ms=max(0, int(duration_ms)) if duration_ms is not None else None,
        error_code=str(error_code)[:64] if error_code else None,
    ))
    db.commit()
