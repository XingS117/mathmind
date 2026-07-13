import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.main import app
from backend.models.operations import AdminAuditEvent, LoginEvent, RuntimeEvent
from backend.models.user import User
from backend.routers import admin as admin_router
from backend.routers import auth as auth_router
from backend.services.auth_service import create_token, hash_password
from backend.services.operations_service import record_runtime_event
from backend.services import ocr_service, llm_service
from backend.routers import upload as upload_router


class OperationsAdminTest(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = handle.name
        handle.close()
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[admin_router.get_db] = override_get_db
        app.dependency_overrides[auth_router.get_db] = override_get_db
        self.client = TestClient(app, raise_server_exceptions=False)
        db = self.SessionLocal()
        try:
            self.admin_id = "u_admin_test"
            self.user_id = "u_user_test"
            self.admin_username = "admin-test"
            self.user_username = "user-test"
            self.admin = User(id=self.admin_id, username=self.admin_username, name="Admin", role="admin", password_hash=hash_password("admin-password"))
            self.user = User(id=self.user_id, username=self.user_username, name="User", role="user", password_hash=hash_password("old-password"))
            db.add_all([self.admin, self.user])
            db.commit()
        finally:
            db.close()
        self.admin_headers = {"Authorization": f"Bearer {create_token(self.admin_id)}"}

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()
        os.unlink(self.db_path)

    def test_non_admin_is_forbidden(self):
        response = self.client.get("/api/v1/admin/accounts-overview")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_update_status_but_not_disable_self_and_audits(self):
        blocked = self.client.patch(f"/api/v1/admin/users/{self.admin_id}/status", json={"is_active": False}, headers=self.admin_headers)
        self.assertEqual(blocked.status_code, 400)

        disabled = self.client.patch(f"/api/v1/admin/users/{self.user_id}/status", json={"is_active": False}, headers=self.admin_headers)
        self.assertEqual(disabled.status_code, 200)
        enabled = self.client.patch(f"/api/v1/admin/users/{self.user_id}/status", json={"is_active": True}, headers=self.admin_headers)
        self.assertEqual(enabled.status_code, 200)
        db = self.SessionLocal()
        try:
            self.assertTrue(db.query(User).filter_by(id=self.user_id).one().is_active)
            self.assertEqual(db.query(AdminAuditEvent).filter_by(target_user_id=self.user_id).count(), 2)
        finally:
            db.close()

    def test_reset_password_allows_login_and_audits(self):
        response = self.client.post(f"/api/v1/admin/users/{self.user_id}/reset-password", json={"new_password": "new-password"}, headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        login = self.client.post("/api/v1/auth/login", json={"username": self.user_username, "password": "new-password"})
        self.assertEqual(login.status_code, 200)
        db = self.SessionLocal()
        try:
            self.assertEqual(db.query(AdminAuditEvent).filter_by(target_user_id=self.user_id, action="reset_password").count(), 1)
        finally:
            db.close()

    def test_accounts_overview_exposes_only_safe_login_metadata(self):
        db = self.SessionLocal()
        try:
            db.add(LoginEvent(id="le_1", user_id=self.user_id, outcome="success", ip_masked="203.0.113.*", ip_fingerprint="secret-full-ip-hash", user_agent_family="Chrome"))
            db.commit()
        finally:
            db.close()
        response = self.client.get("/api/v1/admin/accounts-overview", headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        account = next(item for item in response.json()["accounts"] if item["id"] == self.user_id)
        self.assertEqual(set(account), {"id", "username", "name", "is_active", "created_at", "login_count", "last_login_at", "last_ip_masked", "user_agent_family"})
        self.assertEqual(account["last_ip_masked"], "203.0.113.*")
        self.assertNotIn("203.0.113.9", str(account))
        self.assertNotIn("secret-full-ip-hash", str(account))
        self.assertNotIn("password", str(account).lower())

    def test_runtime_event_whitelist_and_runtime_overview_aggregation(self):
        db = self.SessionLocal()
        try:
            record_runtime_event(db, "question_analysis", "text", "openai", "gpt-test", "success", 10)
            record_runtime_event(db, "question_analysis", "text", "openai", "gpt-test", "success", 30)
            event = db.query(RuntimeEvent).first()
            self.assertEqual(set(event.__dict__) - {"_sa_instance_state"}, {"id", "occurred_at", "feature", "engine_kind", "provider", "model_name", "outcome", "duration_ms", "error_code"})
        finally:
            db.close()
        response = self.client.get("/api/v1/admin/runtime-overview", headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        row = response.json()["events"][0]
        self.assertEqual(row["count"], 2)
        self.assertEqual(row["avg_duration_ms"], 20)
        self.assertEqual(set(row), {"feature", "engine_kind", "provider", "model_name", "outcome", "count", "avg_duration_ms"})


if __name__ == "__main__":
    unittest.main()


class RuntimeInstrumentationTest(unittest.IsolatedAsyncioTestCase):
    async def test_ocr_records_only_allowlisted_metadata(self):
        fake_db = Mock()
        fake_ocr = Mock()
        fake_ocr.predict.return_value = [{"rec_texts": ["题目文本"]}]
        with (
            patch.object(ocr_service, "get_ocr", return_value=fake_ocr),
            patch.object(ocr_service, "_mock_mode", False),
            patch("backend.services.ocr_service.SessionLocal", return_value=fake_db),
            patch("backend.services.ocr_service.record_runtime_event") as record,
        ):
            result = await ocr_service.ocr_image(b"image-bytes")
        self.assertEqual(result, "题目文本")
        kwargs = record.call_args.kwargs
        self.assertEqual(set(kwargs), {"feature", "engine_kind", "provider", "model_name", "outcome", "duration_ms", "error_code"})
        self.assertNotIn("image_bytes", kwargs)

    async def test_text_llm_records_only_allowlisted_metadata(self):
        fake_db = Mock()
        with (
            patch("backend.services.llm_service.SessionLocal", return_value=fake_db),
            patch("backend.services.llm_service.record_runtime_event") as record,
        ):
            result = await llm_service.call_llm_with_config("secret prompt", {"model_provider": "mock", "api_key": "secret-key", "model_name": "test-model"})
        self.assertEqual(result, "")
        kwargs = record.call_args.kwargs
        self.assertEqual(set(kwargs), {"feature", "engine_kind", "provider", "model_name", "outcome", "duration_ms", "error_code"})
        self.assertNotIn("prompt", kwargs)
        self.assertNotIn("api_key", kwargs)

    def test_vision_runtime_records_only_allowlisted_metadata(self):
        fake_db = Mock()
        config = {"model_provider": "openai", "model_name": "gpt-4o", "api_key": "secret-key"}
        with (
            patch("backend.routers.upload.SessionLocal", return_value=fake_db),
            patch("backend.routers.upload.record_runtime_event") as record,
        ):
            upload_router._record_vision_runtime(config, "success", 0.0)
        kwargs = record.call_args.kwargs
        self.assertEqual(set(kwargs), {"feature", "engine_kind", "provider", "model_name", "outcome", "duration_ms", "error_code"})
        self.assertNotIn("api_key", kwargs)
