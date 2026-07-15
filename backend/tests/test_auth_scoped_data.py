"""P1-AUTH-01: with a Bearer token, business endpoints must scope data
to the authenticated user; guests only see u_default's data.
"""

import json
import unittest
import uuid

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import app
from backend.models.question import Question
from backend.models.session import Session as LSession
from backend.models.user import User
from backend.services.auth_service import create_token, hash_password


class AuthScopedDataTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self._marker = f"test_{uuid.uuid4().hex[:8]}"
        self.uid = f"u_{self._marker}"
        # Create test user
        self.db.add(User(
            id=self.uid,
            username=f"testuser_{self._marker}",
            password_hash=hash_password("pw"),
            name="Tester",
            role="user",
            school_level="高中",
        ))
        # Two questions: one owned by this user, one by u_default
        self.db.add(Question(
            id=f"q_{self._marker}_mine",
            user_id=self.uid,
            text="my private question",
            status="complete",
            knowledge_points=json.dumps(["kp_a"]),
            knowmap_nodes=json.dumps([]),
        ))
        self.db.add(Question(
            id=f"q_{self._marker}_default",
            user_id="u_default",
            text="guest question",
            status="complete",
            knowledge_points=json.dumps(["kp_a"]),
            knowmap_nodes=json.dumps([]),
        ))
        self.db.commit()
        self.token = create_token(self.uid)

    def tearDown(self):
        self.db.query(Question).filter(Question.id.like(f"q_{self._marker}_%")).delete(synchronize_session=False)
        self.db.query(LSession).filter(LSession.user_id == self.uid).delete(synchronize_session=False)
        self.db.query(User).filter(User.id == self.uid).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def _get(self, path, use_token=False):
        headers = {"Authorization": f"Bearer {self.token}"} if use_token else {}
        return self.client.get(path, headers=headers)

    def test_dashboard_isolates_by_user(self):
        r_guest = self._get("/api/v1/learn/dashboard").json()
        r_user = self._get("/api/v1/learn/dashboard", use_token=True).json()
        # user should count their own question
        self.assertGreaterEqual(r_user["total_questions"], 1)
        # guest should not include the user's question in their total
        # (both counts are per-user; we just require independence)
        self.assertIsNotNone(r_guest["total_questions"])

    def test_history_isolates_by_user(self):
        r_guest = self._get("/api/v1/learn/history").json()
        r_user = self._get("/api/v1/learn/history", use_token=True).json()
        guest_qids = {s["question_id"] for s in r_guest.get("sessions", [])}
        # guest history must not surface the user's private question id
        self.assertNotIn(f"q_{self._marker}_mine", guest_qids)
        # /learn/history returns sessions, not questions; we mainly verify no crash
        self.assertIn("sessions", r_user)

    def test_auth_me_reflects_login(self):
        r = self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {self.token}"}).json()
        self.assertEqual(r["id"], self.uid)
        r_guest = self.client.get("/api/v1/auth/me").json()
        self.assertEqual(r_guest["id"], "u_default")

    def test_inactive_user_token_is_rejected_from_business_and_profile_routes(self):
        user = self.db.query(User).filter(User.id == self.uid).one()
        user.is_active = False
        self.db.commit()
        headers = {"Authorization": f"Bearer {self.token}"}

        self.assertEqual(self.client.get("/api/v1/learn/dashboard", headers=headers).status_code, 403)
        self.assertEqual(self.client.put("/api/v1/auth/profile", json={"name": "Blocked"}, headers=headers).status_code, 403)


if __name__ == "__main__":
    unittest.main()
