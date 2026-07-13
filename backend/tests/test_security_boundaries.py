import io
import os
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import app
from backend.models.question import Question
from backend.models.settings import UserSettings
from backend.models.user import User
from backend.services.auth_service import create_token, hash_password
from backend.routers import upload as upload_router


class SecurityBoundariesTest(unittest.TestCase):
    def setUp(self):
        self.marker = uuid.uuid4().hex[:10]
        self.user_id = f"u_secure_{self.marker}"
        self.other_id = f"u_other_{self.marker}"
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.db.add_all([
            User(id=self.user_id, username=f"secure_{self.marker}", name="Secure", role="user", password_hash=hash_password("password-123")),
            User(id=self.other_id, username=f"other_{self.marker}", name="Other", role="user", password_hash=hash_password("password-123")),
            Question(id=f"q_secure_{self.marker}", user_id=self.user_id, text="private", status="complete"),
        ])
        self.db.commit()
        self.headers = {"Authorization": f"Bearer {create_token(self.user_id)}"}
        self.other_headers = {"Authorization": f"Bearer {create_token(self.other_id)}"}

    def tearDown(self):
        self.db.query(Question).filter(Question.id == f"q_secure_{self.marker}").delete(synchronize_session=False)
        self.db.query(User).filter(User.id.in_([self.user_id, self.other_id])).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_model_config_requires_auth_and_never_returns_secret(self):
        self.assertEqual(self.client.get("/api/v1/settings/models").status_code, 401)
        put = self.client.put("/api/v1/settings/models", headers=self.headers, json={
            "model_provider": "openai", "model_name": "gpt-test", "api_key": "student-secret", "base_url": "https://api.openai.com/v1",
        })
        self.assertEqual(put.status_code, 200)
        self.assertNotIn("student-secret", put.text)
        self.assertTrue(put.json()["api_key_configured"])
        get = self.client.get("/api/v1/settings/models", headers=self.headers)
        self.assertEqual(get.status_code, 200)
        self.assertNotIn("student-secret", get.text)
        retain = self.client.put("/api/v1/settings/models", headers=self.headers, json={
            "model_provider": "openai", "model_name": "gpt-test", "api_key": "", "base_url": "https://api.openai.com/v1",
        })
        self.assertEqual(retain.status_code, 200)
        self.assertEqual(self.db.query(UserSettings).filter_by(user_id=self.user_id).one().api_key, "student-secret")

    def test_model_test_rejects_non_allowlisted_url(self):
        response = self.client.post("/api/v1/settings/models/test", headers=self.headers, json={
            "model_provider": "openai", "model_name": "gpt-test", "api_key": "secret", "base_url": "http://127.0.0.1:8000",
        })
        self.assertEqual(response.status_code, 400)

    def test_upload_requires_auth_and_never_uses_admin_config(self):
        denied = self.client.post("/api/v1/questions/analyze", files={"image": ("q.png", io.BytesIO(b"png"), "image/png")})
        self.assertEqual(denied.status_code, 401)
        with patch.dict(os.environ, {"MATHMIND_LLM_API_KEY": "", "DEEPSEEK_API_KEY": ""}):
            has_llm, config = upload_router._get_llm_config(self.user_id)
        self.assertFalse(has_llm)
        self.assertIsNone(config)

    def test_question_status_is_scoped_to_owner(self):
        response = self.client.get(f"/api/v1/questions/q_secure_{self.marker}/status", headers=self.other_headers)
        self.assertEqual(response.status_code, 404)

    def test_confirmation_rejects_oversized_model_input_before_calling_model(self):
        with patch("backend.routers.upload.call_llm_with_config") as call_model:
            response = self.client.post("/api/v1/questions/confirm", headers=self.headers, json={
                "text": "x" * 12001,
                "raw_ocr_text": "x" * 12001,
            })
        self.assertEqual(response.status_code, 400)
        call_model.assert_not_called()

    def test_legacy_unsafe_model_url_is_rejected_before_any_model_call(self):
        self.db.add(UserSettings(user_id=self.user_id, model_provider="openai", model_name="gpt-test", api_key="secret", base_url="http://127.0.0.1:8000"))
        self.db.commit()
        with patch.dict(os.environ, {"MATHMIND_LLM_API_KEY": "", "DEEPSEEK_API_KEY": ""}), patch("backend.routers.upload.call_llm_with_config") as call_model:
            analyze = self.client.post("/api/v1/questions/analyze", headers=self.headers, files={"image": ("q.png", io.BytesIO(b"png"), "image/png")})
            confirm = self.client.post("/api/v1/questions/confirm", headers=self.headers, json={"text": "x=1"})
        self.assertEqual(analyze.status_code, 400)
        self.assertEqual(confirm.status_code, 400)
        call_model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
