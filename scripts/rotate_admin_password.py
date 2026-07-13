"""Rotate the existing administrator password from an explicitly configured ADMIN_PASS."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from backend.database import SessionLocal
from backend.models.user import User
from backend.services.auth_service import hash_password
from backend.services.runtime_config import DEFAULT_ADMIN_PASS, load_runtime_config


def main() -> int:
    config = load_runtime_config()
    if config.admin_pass == DEFAULT_ADMIN_PASS:
        raise RuntimeError("Set a non-default ADMIN_PASS explicitly before rotating the administrator password.")

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            raise RuntimeError("No administrator account exists; start the service once after setting ADMIN_PASS.")
        admin.password_hash = hash_password(config.admin_pass)
        db.commit()
    finally:
        db.close()
    print("Administrator password rotated.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"Rotation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
