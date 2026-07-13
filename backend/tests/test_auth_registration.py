import hashlib
import os
import tempfile
import unittest
import uuid

from sqlalchemy import create_engine, text
from fastapi.testclient import TestClient

import backend.database as database
from backend.main import app
from backend.models.operations import LoginEvent
from backend.models.user import User
from backend.services.auth_service import hash_password, needs_password_upgrade, verify_password
from backend.services.operations_service import fingerprint_ip


def legacy_hash(password: str) -> str:
    salt = "legacy-salt"
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${digest}"


class PasswordMigrationTest(unittest.TestCase):
    def test_new_password_hash_uses_scrypt_and_verifies(self):
        encoded = hash_password("pw-123456")

        self.assertTrue(encoded.startswith("scrypt$"))
        self.assertTrue(verify_password("pw-123456", encoded))
        self.assertFalse(needs_password_upgrade(encoded))

    def test_legacy_password_is_accepted_then_marked_for_upgrade(self):
        encoded = legacy_hash("pw-123456")

        self.assertTrue(verify_password("pw-123456", encoded))
        self.assertTrue(needs_password_upgrade(encoded))


class DatabaseMigrationTest(unittest.TestCase):
    def test_init_db_adds_is_active_to_legacy_users_table(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
            db_path = handle.name
        temp_engine = create_engine(f"sqlite:///{db_path}")
        original_engine = database.engine
        try:
            with temp_engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE users (
                        id VARCHAR PRIMARY KEY,
                        username VARCHAR NOT NULL UNIQUE,
                        password_hash VARCHAR,
                        name VARCHAR NOT NULL,
                        role VARCHAR,
                        school_level VARCHAR,
                        created_at DATETIME
                    )
                """))

            database.engine = temp_engine
            database.init_db()
            database.init_db()

            with temp_engine.connect() as conn:
                columns = {row[1] for row in conn.execute(text("PRAGMA table_info(users)"))}
            self.assertIn("is_active", columns)
            self.assertIn("updated_at", columns)
        finally:
            database.engine = original_engine
            temp_engine.dispose()
            os.unlink(db_path)


class PublicAuthFlowTest(unittest.TestCase):
    marker = "auth-test-"

    def setUp(self):
        self.client = TestClient(app)
        self.username = f"{self.marker}{uuid.uuid4().hex[:16]}"
        self.password = "password-123"
        self.test_ip = f"203.0.113.{int(uuid.uuid4().hex[:2], 16) or 1}"
        self.headers = {"X-Forwarded-For": self.test_ip, "User-Agent": "AuthTest/1.0"}

    def tearDown(self):
        db = database.SessionLocal()
        try:
            user_ids = [row[0] for row in db.query(User.id).filter(User.username.like(f"{self.marker}%")).all()]
            if user_ids:
                db.query(LoginEvent).filter(LoginEvent.user_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(LoginEvent).filter(LoginEvent.ip_fingerprint == fingerprint_ip(self.test_ip)).delete(synchronize_session=False)
            db.query(User).filter(User.username.like(f"{self.marker}%")).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

    def register(self, username=None, password=None, name="注册测试用户"):
        return self.client.post(
            "/api/v1/auth/register",
            json={"username": username or self.username, "password": password or self.password, "name": name},
            headers=self.headers,
        )

    def test_register_login_and_update_display_name(self):
        registered = self.register()
        self.assertEqual(registered.status_code, 201)
        self.assertEqual(registered.json()["user"]["name"], "注册测试用户")

        logged_in = self.client.post(
            "/api/v1/auth/login", json={"username": self.username, "password": self.password}, headers=self.headers
        )
        self.assertEqual(logged_in.status_code, 200)
        token = logged_in.json()["token"]

        updated = self.client.put(
            "/api/v1/auth/profile", json={"name": "新昵称"}, headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "新昵称")

    def test_duplicate_username_returns_conflict(self):
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(self.register().status_code, 409)

    def test_unknown_username_and_wrong_password_have_same_message(self):
        self.assertEqual(self.register().status_code, 201)
        unknown = self.client.post(
            "/api/v1/auth/login", json={"username": f"{self.marker}missing", "password": self.password}, headers=self.headers
        )
        wrong_password = self.client.post(
            "/api/v1/auth/login", json={"username": self.username, "password": "wrong-password"}, headers=self.headers
        )
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unknown.json()["detail"], wrong_password.json()["detail"])

    def test_disabled_user_cannot_log_in(self):
        self.assertEqual(self.register().status_code, 201)
        db = database.SessionLocal()
        try:
            db.query(User).filter(User.username == self.username).update({User.is_active: False})
            db.commit()
        finally:
            db.close()

        response = self.client.post(
            "/api/v1/auth/login", json={"username": self.username, "password": self.password}, headers=self.headers
        )
        self.assertEqual(response.status_code, 403)

    def test_sixth_failed_login_from_same_ip_is_rate_limited(self):
        self.assertEqual(self.register().status_code, 201)
        for _ in range(5):
            response = self.client.post(
                "/api/v1/auth/login", json={"username": self.username, "password": "wrong-password"}, headers=self.headers
            )
            self.assertEqual(response.status_code, 401)
        response = self.client.post(
            "/api/v1/auth/login", json={"username": self.username, "password": "wrong-password"}, headers=self.headers
        )
        self.assertEqual(response.status_code, 429)

    def test_login_events_only_store_masked_and_fingerprinted_ip(self):
        self.assertEqual(self.register().status_code, 201)
        self.client.post(
            "/api/v1/auth/login", json={"username": self.username, "password": self.password}, headers=self.headers
        )
        db = database.SessionLocal()
        try:
            user = db.query(User).filter(User.username == self.username).one()
            event = db.query(LoginEvent).filter(LoginEvent.user_id == user.id).order_by(LoginEvent.occurred_at.desc()).first()
            self.assertIsNotNone(event)
            self.assertNotIn(self.test_ip, event.ip_masked)
            self.assertNotIn(self.test_ip, event.ip_fingerprint)
            self.assertTrue(event.ip_fingerprint)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
