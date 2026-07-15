import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.main import app
from backend.models.operations import AdminAuditEvent, LoginEvent, RuntimeEvent
from backend.models.referral import ReferralAttribution, ReferralLink, ReferralVisit
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

    def test_disabled_admin_cannot_use_existing_token(self):
        db = self.SessionLocal()
        try:
            db.query(User).filter_by(id=self.admin_id).update({User.is_active: False})
            db.commit()
        finally:
            db.close()
        response = self.client.get("/api/v1/admin/accounts-overview", headers=self.admin_headers)
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

    def test_create_and_delete_user_are_audited(self):
        created = self.client.post(
            "/api/v1/admin/users", json={"username": "audit-user", "password": "password-123", "name": "Audit"},
            headers=self.admin_headers,
        )
        self.assertEqual(created.status_code, 200)
        user_id = created.json()["id"]
        deleted = self.client.delete(f"/api/v1/admin/users/{user_id}", headers=self.admin_headers)
        self.assertEqual(deleted.status_code, 200)
        db = self.SessionLocal()
        try:
            actions = [row.action for row in db.query(AdminAuditEvent).filter_by(target_user_id=user_id).all()]
            self.assertEqual(actions, ["create_user", "delete_user"])
        finally:
            db.close()

    def test_admin_password_endpoints_enforce_eight_to_128_characters(self):
        for password in ("a" * 7, "a" * 129):
            with self.subTest(password_length=len(password)):
                created = self.client.post(
                    "/api/v1/admin/users",
                    json={"username": f"boundary-{len(password)}", "password": password, "name": "边界用户"},
                    headers=self.admin_headers,
                )
                self.assertEqual(created.status_code, 400)
                reset = self.client.post(
                    f"/api/v1/admin/users/{self.user_id}/reset-password",
                    json={"new_password": password}, headers=self.admin_headers,
                )
                self.assertEqual(reset.status_code, 400)

        for password in ("a" * 8, "a" * 128):
            with self.subTest(password_length=len(password)):
                reset = self.client.post(
                    f"/api/v1/admin/users/{self.user_id}/reset-password",
                    json={"new_password": password}, headers=self.admin_headers,
                )
                self.assertEqual(reset.status_code, 200)

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

    def test_accounts_overview_chooses_one_latest_login_when_timestamps_match(self):
        same_second = datetime(2026, 7, 13, 9, 0, 0)
        db = self.SessionLocal()
        try:
            db.add_all([
                LoginEvent(id="le_same_a", user_id=self.user_id, outcome="success", occurred_at=same_second, ip_masked="198.51.100.*", ip_fingerprint="hash-a", user_agent_family="Firefox"),
                LoginEvent(id="le_same_b", user_id=self.user_id, outcome="success", occurred_at=same_second, ip_masked="203.0.113.*", ip_fingerprint="hash-b", user_agent_family="Chrome"),
            ])
            db.commit()
        finally:
            db.close()
        response = self.client.get("/api/v1/admin/accounts-overview", headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        matches = [item for item in response.json()["accounts"] if item["id"] == self.user_id]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["last_ip_masked"], "203.0.113.*")
        self.assertEqual(matches[0]["user_agent_family"], "Chrome")

    def test_accounts_overview_uses_bounded_queries_for_multiple_users(self):
        db = self.SessionLocal()
        try:
            for index in range(4):
                db.add(User(id=f"u_extra_{index}", username=f"extra-{index}", name="Extra", role="user", password_hash="hash"))
            db.commit()
        finally:
            db.close()
        statements = []

        def observe(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(self.engine, "before_cursor_execute", observe)
        try:
            response = self.client.get("/api/v1/admin/accounts-overview", headers=self.admin_headers)
        finally:
            event.remove(self.engine, "before_cursor_execute", observe)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()["accounts"]), 6)
        self.assertLessEqual(len(statements), 2)

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

    def test_operations_overview_is_admin_only_and_returns_safe_aggregates(self):
        denied = self.client.get("/api/v1/admin/operations-overview")
        self.assertEqual(denied.status_code, 403)
        empty = self.client.get("/api/v1/admin/operations-overview", headers=self.admin_headers)
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json(), {
            "funnel": {"visits": 0, "registrations": 0, "first_questions": 0, "first_tutors": 0},
            "runtime_health": [],
        })

        db = self.SessionLocal()
        try:
            link = ReferralLink(id="rl_operations", owner_user_id=self.admin_id, code="share-code")
            visit = ReferralVisit(id="rv_operations", referral_id=link.id)
            attribution = ReferralAttribution(
                id="ra_operations", inviter_user_id=self.admin_id, invitee_user_id=self.user_id,
                visit_id=visit.id, first_question_at=datetime(2026, 7, 14, 9, 0, 0),
            )
            db.add_all([link, visit, attribution,
                RuntimeEvent(id="re_success", feature="question_analysis", engine_kind="text", provider="openai", model_name="gpt-test", outcome="success", duration_ms=40),
                RuntimeEvent(id="re_failure", feature="question_analysis", engine_kind="text", provider="openai", model_name="gpt-test", outcome="failed", duration_ms=20, error_code="upstream"),
                RuntimeEvent(id="re_tutor", feature="tutor", engine_kind="text", provider="openai", model_name="gpt-test", outcome="success", duration_ms=10),
            ])
            db.commit()
        finally:
            db.close()

        response = self.client.get("/api/v1/admin/operations-overview", headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["funnel"], {"visits": 1, "registrations": 1, "first_questions": 1, "first_tutors": 0})
        self.assertEqual(payload["runtime_health"], [{
            "feature": "question_analysis", "engine_kind": "text", "provider": "openai", "model_name": "gpt-test",
            "count": 2, "success_rate": 0.5, "avg_duration_ms": 30,
        }, {
            "feature": "tutor", "engine_kind": "text", "provider": "openai", "model_name": "gpt-test",
            "count": 1, "success_rate": 1, "avg_duration_ms": 10,
        }])
        self.assertNotIn(self.user_id, str(payload))
        self.assertNotIn(self.user_username, str(payload))
        self.assertNotIn("share-code", str(payload))
        self.assertNotIn("error_code", str(payload))


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

    async def test_telemetry_session_failure_does_not_break_ocr_or_llm(self):
        fake_ocr = Mock()
        fake_ocr.predict.return_value = [{"rec_texts": ["题目文本"]}]
        with (
            patch.object(ocr_service, "get_ocr", return_value=fake_ocr),
            patch.object(ocr_service, "_mock_mode", False),
            patch("backend.services.ocr_service.SessionLocal", side_effect=RuntimeError("database unavailable")),
        ):
            self.assertEqual(await ocr_service.ocr_image(b"image-bytes"), "题目文本")
        with patch("backend.services.llm_service.SessionLocal", side_effect=RuntimeError("database unavailable")):
            self.assertEqual(await llm_service.call_llm_with_config("secret prompt", {"model_provider": "mock"}), "")

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
