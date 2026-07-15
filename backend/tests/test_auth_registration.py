import hashlib
import importlib
import os
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession, sessionmaker
from fastapi.testclient import TestClient

import backend.database as database
from backend.database import Base
from backend.main import app
from backend.routers import auth as auth_router
from backend.models.operations import LoginEvent
from backend.models.user import User
from backend.services.auth_service import hash_password, needs_password_upgrade, verify_password
from backend.services.operations_service import fingerprint_ip
from backend.services.rate_limit_service import SlidingWindowRateLimiter, rate_limiter


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
    marker = "authtest"

    def setUp(self):
        self.real_db_hash = self._file_hash(database.DB_PATH)
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
            self.db_path = handle.name
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_router.get_db] = override_get_db
        self.client = TestClient(app, raise_server_exceptions=False)
        rate_limiter._attempts.clear()
        self.username = f"{self.marker}{uuid.uuid4().hex[:16]}"
        self.password = "password-123"
        self.test_ip = f"203.0.113.{int(uuid.uuid4().hex[:2], 16) or 1}"
        self.headers = {"X-Forwarded-For": self.test_ip, "User-Agent": "AuthTest/1.0"}

    def tearDown(self):
        try:
            app.dependency_overrides.pop(auth_router.get_db, None)
            self.engine.dispose()
            os.unlink(self.db_path)
            self.assertEqual(self.real_db_hash, self._file_hash(database.DB_PATH))
        finally:
            rate_limiter._attempts.clear()

    @staticmethod
    def _file_hash(path):
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()

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

    def test_registration_rejects_non_alphanumeric_usernames_with_explicit_message(self):
        for username in ("中文用户", "user_name", "user-name", "ab", "a" * 33):
            response = self.register(username=username)
            self.assertEqual(response.status_code, 422)
            self.assertTrue(response.json()["detail"][0]["msg"].endswith("用户名仅支持 3–32 位英文字母或数字"))

    def test_registration_accepts_alphanumeric_username_boundaries(self):
        self.assertEqual(self.register(username="abc").status_code, 201)
        self.assertEqual(self.register(username="a" * 32).status_code, 201)

    def test_username_availability_reports_available_and_taken(self):
        available = self.client.get(
            "/api/v1/auth/username-availability", params={"username": "freeuser"}, headers=self.headers
        )
        self.assertEqual(available.status_code, 200)
        self.assertEqual(available.json(), {"available": True})

        self.assertEqual(self.register(username="takenuser").status_code, 201)
        taken = self.client.get(
            "/api/v1/auth/username-availability", params={"username": "takenuser"}, headers=self.headers
        )
        self.assertEqual(taken.status_code, 200)
        self.assertEqual(taken.json(), {"available": False})

    def test_username_availability_reuses_registration_format_rule(self):
        response = self.client.get(
            "/api/v1/auth/username-availability", params={"username": "中文用户"}, headers=self.headers
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "用户名仅支持 3–32 位英文字母或数字")

    def test_username_availability_is_rate_limited(self):
        for _ in range(60):
            response = self.client.get(
                "/api/v1/auth/username-availability", params={"username": "freeuser"}, headers=self.headers
            )
            self.assertEqual(response.status_code, 200)
        response = self.client.get(
            "/api/v1/auth/username-availability", params={"username": "freeuser"}, headers=self.headers
        )
        self.assertEqual(response.status_code, 429)

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

    def test_unknown_and_known_bad_login_both_verify_password_once(self):
        self.assertEqual(self.register().status_code, 201)
        with patch("backend.routers.auth.verify_password", wraps=auth_router.verify_password) as verifier:
            unknown = self.client.post(
                "/api/v1/auth/login", json={"username": f"{self.marker}missing", "password": self.password}, headers=self.headers
            )
            self.assertEqual(unknown.status_code, 401)
            self.assertEqual(verifier.call_count, 1)
            verifier.reset_mock()
            known = self.client.post(
                "/api/v1/auth/login", json={"username": self.username, "password": "wrong-password"}, headers=self.headers
            )
            self.assertEqual(known.status_code, 401)
            self.assertEqual(verifier.call_count, 1)

    def test_registration_integrity_conflict_returns_409(self):
        with patch.object(SQLAlchemySession, "commit", side_effect=IntegrityError("insert", {}, Exception())):
            response = self.register()
        self.assertEqual(response.status_code, 409)

    def test_disabled_user_cannot_log_in(self):
        self.assertEqual(self.register().status_code, 201)
        db = self.SessionLocal()
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

    def test_successful_login_does_not_consume_failed_login_window(self):
        self.assertEqual(self.register().status_code, 201)
        for _ in range(5):
            response = self.client.post(
                "/api/v1/auth/login", json={"username": self.username, "password": "wrong-password"}, headers=self.headers
            )
            self.assertEqual(response.status_code, 401)
        success = self.client.post(
            "/api/v1/auth/login", json={"username": self.username, "password": self.password}, headers=self.headers
        )
        self.assertEqual(success.status_code, 200)
        response = self.client.post(
            "/api/v1/auth/login", json={"username": self.username, "password": "wrong-password"}, headers=self.headers
        )
        self.assertEqual(response.status_code, 429)

    def test_login_events_only_store_masked_and_fingerprinted_ip(self):
        self.assertEqual(self.register().status_code, 201)
        self.client.post(
            "/api/v1/auth/login", json={"username": self.username, "password": self.password}, headers=self.headers
        )
        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.username == self.username).one()
            event = db.query(LoginEvent).filter(LoginEvent.user_id == user.id).order_by(LoginEvent.occurred_at.desc()).first()
            self.assertIsNotNone(event)
            self.assertNotIn(self.test_ip, event.ip_masked)
            self.assertNotIn(self.test_ip, event.ip_fingerprint)
            self.assertTrue(event.ip_fingerprint)
        finally:
            db.close()

    def test_untrusted_forwarded_for_does_not_change_login_event_source(self):
        self.assertEqual(self.register().status_code, 201)
        with patch.dict(os.environ, {"MATHMIND_TRUST_PROXY": ""}, clear=False):
            self.client.post(
                "/api/v1/auth/login", json={"username": self.username, "password": self.password}, headers=self.headers
            )
        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.username == self.username).one()
            event = db.query(LoginEvent).filter(LoginEvent.user_id == user.id).one()
            self.assertEqual(event.ip_masked, "127.0.0.*")
        finally:
            db.close()

    def test_trusted_proxy_uses_first_forwarded_for_value(self):
        self.assertEqual(self.register().status_code, 201)
        forwarded_for = "203.0.113.10, 10.0.0.1"
        headers = {**self.headers, "X-Forwarded-For": forwarded_for}
        with patch.dict(os.environ, {"MATHMIND_TRUST_PROXY": "1"}):
            self.client.post(
                "/api/v1/auth/login", json={"username": self.username, "password": self.password}, headers=headers
            )
        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.username == self.username).one()
            event = db.query(LoginEvent).filter(LoginEvent.user_id == user.id).one()
            self.assertEqual(event.ip_masked, "203.0.113.*")
            self.assertEqual(event.ip_fingerprint, fingerprint_ip("203.0.113.10"))
            self.assertNotEqual(event.ip_fingerprint, fingerprint_ip("10.0.0.1"))
        finally:
            db.close()


class RateLimitServiceTest(unittest.TestCase):
    def test_concurrent_calls_do_not_exceed_limit(self):
        limiter = SlidingWindowRateLimiter()
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(lambda _: limiter.allow("same-ip", "login", 5), range(100)))
        self.assertEqual(sum(results), 5)

    def test_sweeps_once_per_interval_then_sweeps_after_interval(self):
        limiter = SlidingWindowRateLimiter()
        timestamps = [100 + index / 100 for index in range(100)] + [106]
        with patch("backend.services.rate_limit_service.time.monotonic", side_effect=timestamps):
            with patch.object(limiter, "_remove_expired", wraps=limiter._remove_expired) as sweep:
                for index in range(100):
                    limiter.allow(f"ip-{index}", "login", 1)
                self.assertEqual(sweep.call_count, 1)
                limiter.allow("after-interval", "login", 1)
                self.assertEqual(sweep.call_count, 2)

    def test_current_key_expires_exactly_at_window_boundary_between_global_sweeps(self):
        limiter = SlidingWindowRateLimiter()
        with patch("backend.services.rate_limit_service.time.monotonic", side_effect=[0, 0, 0, 0, 0, 299, 300]):
            for _ in range(5):
                self.assertTrue(limiter.allow("target", "login", 5))
            self.assertTrue(limiter.allow("other", "login", 1))
            self.assertTrue(limiter.allow("target", "login", 5))

    def test_expired_keys_are_swept_and_tracking_is_bounded(self):
        limiter = SlidingWindowRateLimiter()
        with patch("backend.services.rate_limit_service.time.monotonic", return_value=0):
            for index in range(10050):
                limiter.allow(f"expired-{index}", "register", 1)
        self.assertLessEqual(len(limiter._attempts), 10000)
        with patch("backend.services.rate_limit_service.time.monotonic", return_value=301):
            limiter.allow("fresh", "register", 1)
        self.assertEqual(len(limiter._attempts), 1)


class OperationsSecurityTest(unittest.TestCase):
    def test_ip_fingerprint_uses_configured_secret_and_not_repository_constant(self):
        import backend.services.operations_service as operations_service

        original_env = os.environ.copy()
        try:
            with patch.dict(os.environ, {"MATHMIND_IP_HASH_SECRET": "test-secret"}, clear=False):
                operations_service = importlib.reload(operations_service)
                configured = operations_service.fingerprint_ip("203.0.113.77")
            with patch.dict(os.environ, {}, clear=True):
                operations_service = importlib.reload(operations_service)
                generated_once = operations_service.fingerprint_ip("203.0.113.77")
                operations_service = importlib.reload(operations_service)
                generated_twice = operations_service.fingerprint_ip("203.0.113.77")

            fixed_default = hashlib.sha256(b"mathmind-ip-fingerprint:203.0.113.77").hexdigest()
            self.assertNotEqual(configured, fixed_default)
            self.assertNotEqual(generated_once, fixed_default)
            self.assertNotEqual(generated_once, generated_twice)
        finally:
            os.environ.clear()
            os.environ.update(original_env)
            importlib.reload(operations_service)


if __name__ == "__main__":
    unittest.main()
