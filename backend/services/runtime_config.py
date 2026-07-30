"""Validated runtime settings for security-sensitive deployment configuration."""

from dataclasses import dataclass
import logging
import os
from collections.abc import Mapping


logger = logging.getLogger(__name__)

DEFAULT_JWT_SECRET = "mathmind-dev-secret-key-change-in-prod"
DEFAULT_ADMIN_PASS = "admin123"


@dataclass(frozen=True)
class RuntimeConfig:
    environment: str
    jwt_secret: str
    ip_hash_secret: str | None
    admin_pass: str


def load_runtime_config(environ: Mapping[str, str] | None = None) -> RuntimeConfig:
    """Load settings without process startup side effects."""
    values = os.environ if environ is None else environ
    environment = values.get("MATHMIND_ENV", "development").strip().lower() or "development"
    jwt_secret = values.get("JWT_SECRET", "").strip()
    ip_hash_secret = values.get("MATHMIND_IP_HASH_SECRET", "").strip()
    admin_pass = values.get("ADMIN_PASS", "").strip()

    if environment == "production":
        invalid = []
        if not jwt_secret or jwt_secret == DEFAULT_JWT_SECRET:
            invalid.append("JWT_SECRET")
        if not ip_hash_secret:
            invalid.append("MATHMIND_IP_HASH_SECRET")
        if not admin_pass or admin_pass == DEFAULT_ADMIN_PASS:
            invalid.append("ADMIN_PASS")
        if invalid:
            raise RuntimeError("Production configuration requires secure values for: " + ", ".join(invalid))
        return RuntimeConfig(environment, jwt_secret, ip_hash_secret, admin_pass)

    if not jwt_secret:
        logger.warning("Using development fallback for JWT_SECRET; never use it in production.")
        jwt_secret = DEFAULT_JWT_SECRET
    if not ip_hash_secret:
        logger.warning("MATHMIND_IP_HASH_SECRET is unset; development fingerprint values change after restart.")
    if not admin_pass:
        logger.warning("Using development fallback for ADMIN_PASS; change it before production.")
        admin_pass = DEFAULT_ADMIN_PASS
    return RuntimeConfig(environment, jwt_secret, ip_hash_secret or None, admin_pass)
