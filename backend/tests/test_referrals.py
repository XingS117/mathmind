import asyncio
import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.requests import Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.main import app
from backend.models.user import User
from backend.models.referral import ReferralAttribution, ReferralLink, ReferralVisit
from backend.routers import auth as auth_router
from backend.routers import referral as referral_router
from backend.routers import tutor as tutor_router
from backend.routers import upload as upload_router
from backend.models.session import Session as TutorSession
from backend.schemas.api_schemas import TutorMessageRequest
from backend.routers.upload import ConfirmRequest
from backend.services.auth_service import create_token
from backend.services.rate_limit_service import rate_limiter
from backend.services.referral_service import (
    attribute_registration,
    create_or_get_referral,
    mark_first_learning_milestone,
    owner_stats,
    record_referral_visit,
)


class ReferralFlowTest(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db_path = handle.name
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        self.owner = User(id="u_owner", username="owner", name="分享者", role="user", is_active=True)
        self.invitee = User(id="u_invitee", username="invitee", name="受邀者", role="user", is_active=True)
        self.db.add_all([self.owner, self.invitee])
        self.db.commit()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[referral_router.get_db] = override_get_db
        app.dependency_overrides[auth_router.get_db] = override_get_db
        self.client = TestClient(app)
        rate_limiter._attempts.clear()

    def tearDown(self):
        app.dependency_overrides.pop(referral_router.get_db, None)
        app.dependency_overrides.pop(auth_router.get_db, None)
        rate_limiter._attempts.clear()
        self.db.close()
        self.engine.dispose()
        os.unlink(self.db_path)

    def test_unknown_code_does_not_create_a_visit(self):
        self.assertIsNone(record_referral_visit(self.db, "missing"))
        self.assertEqual(self.db.query(ReferralVisit).count(), 0)
        response = self.client.post("/api/v1/referrals/visit/missing")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.db.query(ReferralVisit).count(), 0)

    def test_visit_rate_limit_rejects_without_creating_another_visit(self):
        link = create_or_get_referral(self.db, self.owner.id)
        self.db.commit()

        for _ in range(20):
            self.assertEqual(self.client.post(f"/api/v1/referrals/visit/{link.code}").status_code, 201)
        rejected = self.client.post(f"/api/v1/referrals/visit/{link.code}")

        self.assertEqual(rejected.status_code, 429)
        self.assertEqual(self.db.query(ReferralVisit).count(), 20)

    def test_visit_endpoint_returns_opaque_id_and_owner_summary_hides_invitee_identity(self):
        link = create_or_get_referral(self.db, self.owner.id)
        self.db.commit()
        visit_response = self.client.post(f"/api/v1/referrals/visit/{link.code}")
        self.assertEqual(visit_response.status_code, 201)
        visit_id = visit_response.json()["visit_id"]
        self.assertTrue(visit_id)
        self.assertNotIn(link.code, visit_id)

        attribute_registration(self.db, visit_id, self.invitee.id)
        self.db.commit()
        headers = {"Authorization": f"Bearer {create_token(self.owner.id)}"}
        summary = self.client.get("/api/v1/referrals/me", headers=headers)
        self.assertEqual(summary.status_code, 200)
        payload = summary.json()
        self.assertEqual(payload["code"], link.code)
        self.assertTrue(payload["share_url"].startswith("http://testserver/"))
        self.assertEqual(payload["visits"], 1)
        self.assertEqual(payload["registrations"], 1)
        self.assertNotIn("invitee", str(payload).lower())
        self.assertNotIn(self.invitee.id, str(payload))

    def test_registration_and_learning_milestones_are_idempotent(self):
        link = create_or_get_referral(self.db, self.owner.id)
        visit_id = record_referral_visit(self.db, link.code)
        self.assertTrue(attribute_registration(self.db, visit_id, self.invitee.id))
        self.assertFalse(attribute_registration(self.db, visit_id, self.invitee.id))

        self.assertTrue(mark_first_learning_milestone(self.db, self.invitee.id, "first_question"))
        self.assertFalse(mark_first_learning_milestone(self.db, self.invitee.id, "first_question"))
        self.assertTrue(mark_first_learning_milestone(self.db, self.invitee.id, "first_tutor_completed"))
        self.assertFalse(mark_first_learning_milestone(self.db, self.invitee.id, "first_tutor_completed"))

        self.assertEqual(owner_stats(self.db, self.owner.id), {
            "visits": 1,
            "registrations": 1,
            "first_questions": 1,
            "first_tutors": 1,
        })

    def test_self_referral_is_rejected_without_attribution(self):
        link = create_or_get_referral(self.db, self.owner.id)
        visit_id = record_referral_visit(self.db, link.code)

        with self.assertRaises(ValueError):
            attribute_registration(self.db, visit_id, self.owner.id)

        self.assertEqual(self.db.query(ReferralAttribution).count(), 0)

    def test_concurrent_link_creation_returns_one_stable_link(self):
        owner_id = self.owner.id
        insert_barrier = threading.Barrier(2)

        def wait_until_both_workers_have_observed_no_link(*_args):
            # Mapper insertion occurs only after create_or_get_referral's initial
            # lookup returned no link, so this forces the unique-conflict path.
            insert_barrier.wait(timeout=5)

        def create_link():
            db = self.SessionLocal()
            try:
                link = create_or_get_referral(db, owner_id)
                db.commit()
                return link.code
            finally:
                db.close()

        event.listen(ReferralLink, "before_insert", wait_until_both_workers_have_observed_no_link)
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                codes = list(executor.map(lambda _: create_link(), range(2)))
        finally:
            event.remove(ReferralLink, "before_insert", wait_until_both_workers_have_observed_no_link)

        self.assertEqual(codes[0], codes[1])
        self.assertEqual(self.db.query(ReferralLink).filter_by(owner_user_id=owner_id).count(), 1)

    def test_register_upload_and_completed_tutor_mark_attributed_user_once(self):
        link = create_or_get_referral(self.db, self.owner.id)
        visit_id = record_referral_visit(self.db, link.code)
        self.db.commit()

        registered = self.client.post("/api/v1/auth/register", json={
            "username": "newinvitee", "password": "password-123", "name": "新受邀者",
            "referral_visit_id": visit_id,
        })
        self.assertEqual(registered.status_code, 201)
        invitee_id = registered.json()["user"]["id"]
        self.assertIsNotNone(self.db.query(ReferralAttribution).filter_by(invitee_user_id=invitee_id).first())

        request = Request({
            "type": "http",
            "headers": [(b"authorization", f"Bearer {create_token(invitee_id)}".encode())],
        })
        with patch("backend.routers.upload._get_llm_config", return_value=(False, None)):
            asyncio.run(upload_router.confirm_question(ConfirmRequest(text="x=1"), request, self.db))
        self.assertEqual(owner_stats(self.db, self.owner.id)["first_questions"], 1)

        tutor_session = TutorSession(
            id="s_referral", user_id=invitee_id, question_id=self.db.query(upload_router.Question).first().id,
            total_steps=1, current_step=0, steps_json="[]", messages_json="[]", mistakes_json="[]",
        )
        self.db.add(tutor_session)
        self.db.commit()

        def complete_session(session, *_args):
            session.status = "completed"
            return {
                "type": "complete", "reply": "完成", "step_index": 1, "total_steps": 1,
                "hints_remaining": 3, "mastery_update": 0.3, "variant_suggested": None,
            }

        with patch("backend.routers.tutor.process_message", side_effect=complete_session), patch("backend.routers.tutor.schedule_reviews"):
            tutor_router.tutor_message(TutorMessageRequest(session_id=tutor_session.id), request, self.db)
        self.assertEqual(owner_stats(self.db, self.owner.id)["first_tutors"], 1)


if __name__ == "__main__":
    unittest.main()
