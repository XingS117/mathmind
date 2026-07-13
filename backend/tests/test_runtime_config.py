import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.user import User
from backend.services.auth_service import hash_password
from backend.services.runtime_config import RuntimeConfig


class RuntimeConfigTest(unittest.TestCase):
    def test_production_rejects_missing_or_default_secrets(self):
        from backend.services.runtime_config import load_runtime_config

        cases = (
            {"JWT_SECRET": "", "MATHMIND_IP_HASH_SECRET": "ip-secret", "ADMIN_PASS": "secure-admin-pass"},
            {"JWT_SECRET": "mathmind-dev-secret-key-change-in-prod", "MATHMIND_IP_HASH_SECRET": "ip-secret", "ADMIN_PASS": "secure-admin-pass"},
            {"JWT_SECRET": "jwt-secret", "MATHMIND_IP_HASH_SECRET": "", "ADMIN_PASS": "secure-admin-pass"},
            {"JWT_SECRET": "jwt-secret", "MATHMIND_IP_HASH_SECRET": "ip-secret", "ADMIN_PASS": "admin123"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with patch.dict(os.environ, {"MATHMIND_ENV": "production", **overrides}, clear=True):
                    with self.assertRaises(RuntimeError):
                        load_runtime_config()

    def test_development_uses_explicit_fallbacks_and_warns(self):
        from backend.services.runtime_config import (
            DEFAULT_ADMIN_PASS,
            DEFAULT_JWT_SECRET,
            load_runtime_config,
        )

        with patch.dict(os.environ, {"MATHMIND_ENV": "development"}, clear=True):
            with self.assertLogs("backend.services.runtime_config", level="WARNING") as logs:
                config = load_runtime_config()

        self.assertEqual(config.jwt_secret, DEFAULT_JWT_SECRET)
        self.assertEqual(config.admin_pass, DEFAULT_ADMIN_PASS)
        self.assertIsNone(config.ip_hash_secret)
        self.assertIn("development fallback", "\n".join(logs.output))


class ProductionAdminPasswordGateTest(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = handle.name
        handle.close()
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.production_config = RuntimeConfig("production", "jwt-secret", "ip-secret", "rotated-admin-password")

    def tearDown(self):
        self.engine.dispose()
        os.unlink(self.db_path)

    def test_production_rejects_existing_admin_with_legacy_default_password(self):
        from backend.main import ensure_initial_accounts

        db = self.SessionLocal()
        try:
            db.add(User(id="u_admin", username="admin", name="管理员", role="admin", password_hash="salt$" + hashlib.sha256(b"saltadmin123").hexdigest()))
            db.commit()
            with self.assertRaisesRegex(RuntimeError, "rotation"):
                ensure_initial_accounts(db, self.production_config)
        finally:
            db.close()

    def test_production_allows_existing_admin_with_rotated_password(self):
        from backend.main import ensure_initial_accounts

        db = self.SessionLocal()
        try:
            db.add(User(id="u_admin", username="admin", name="管理员", role="admin", password_hash=hash_password("not-the-default-password")))
            db.commit()
            ensure_initial_accounts(db, self.production_config)
        finally:
            db.close()

    def test_production_rejects_existing_admin_with_current_default_password(self):
        from backend.main import ensure_initial_accounts

        db = self.SessionLocal()
        try:
            db.add(User(id="u_admin", username="admin", name="管理员", role="admin", password_hash=hash_password("admin123")))
            db.commit()
            with self.assertRaisesRegex(RuntimeError, "rotation"):
                ensure_initial_accounts(db, self.production_config)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
