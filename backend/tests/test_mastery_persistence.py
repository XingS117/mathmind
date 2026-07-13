import json
import os
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.mastery import Mastery
from backend.models.question import Question
from backend.models.review import ReviewSchedule
from backend.models.session import Session
from backend.models.user import User
from backend.routers.review import complete_review
from backend.routers.review import schedule_reviews
from backend.routers.tutor import create_session, tutor_message
from backend.schemas.api_schemas import TutorMessageRequest, TutorSessionCreate
from backend.services.mastery_service import (
    apply_review_mastery,
    apply_tutor_mastery,
    canonical_question_nodes,
)


class _Request:
    def __init__(self, user_id):
        self.headers = {}
        self._user_id = user_id


class MasteryPersistenceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.db.add_all([
            User(id="u1", username="u1", name="Student 1"),
            User(id="u2", username="u2", name="Student 2"),
        ])
        self.question = Question(
            id="q1", user_id="u1", text="question", status="complete",
            knowmap_nodes=json.dumps(["node_a", " node_b ", "node_a", ""]),
            knowledge_points=json.dumps(["fallback"]),
        )
        self.session = Session(id="s1", user_id="u1", question_id="q1")
        self.db.add_all([self.question, self.session])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_canonical_nodes_fall_back_to_knowledge_points(self):
        question = Question(
            id="q_fallback", user_id="u1", text="question",
            knowmap_nodes=json.dumps([]),
            knowledge_points=json.dumps([" kp_a ", "", "kp_a", "kp_b"]),
        )
        self.assertEqual(canonical_question_nodes(question), ["kp_a", "kp_b"])

    def test_canonical_nodes_fall_back_when_explicit_nodes_are_blank(self):
        question = Question(
            id="q_blank_nodes", user_id="u1", text="question",
            knowmap_nodes=json.dumps(["", "  "]),
            knowledge_points=json.dumps(["kp_a"]),
        )
        self.assertEqual(canonical_question_nodes(question), ["kp_a"])

    def test_completed_tutor_session_updates_each_question_node_once(self):
        self.session.status = "completed"
        self.db.commit()
        result = apply_tutor_mastery(self.db, "u1", self.question, self.session, 0.3)
        self.assertEqual(result.updated_nodes, ["node_a", "node_b"])
        self.assertEqual(
            self.db.query(Mastery).filter_by(user_id="u1", node_id="node_a").one().score,
            0.3,
        )
        apply_tutor_mastery(self.db, "u1", self.question, self.session, 0.3)
        record = self.db.query(Mastery).filter_by(user_id="u1", node_id="node_a").one()
        self.assertEqual(record.score, 0.3)
        self.assertEqual(record.total_sessions, 1)
        self.assertEqual(record.correct_sessions, 1)

    def test_review_round_delta_is_idempotent(self):
        review = ReviewSchedule(
            id="rev_round_3", user_id="u1", question_id="q1", review_round=3,
            scheduled_date=datetime.utcnow() - timedelta(days=1),
        )
        self.db.add(review)
        self.db.commit()

        result = apply_review_mastery(self.db, review)
        self.assertEqual(result.updated_nodes, ["node_a", "node_b"])
        record = self.db.query(Mastery).filter_by(user_id="u1", node_id="node_a").one()
        self.assertEqual(record.score, 0.15)
        self.assertEqual(record.total_sessions, 1)
        self.assertEqual(record.correct_sessions, 1)

        apply_review_mastery(self.db, review)
        record = self.db.query(Mastery).filter_by(user_id="u1", node_id="node_a").one()
        self.assertEqual(record.score, 0.15)
        self.assertEqual(record.total_sessions, 1)

    def test_each_review_round_uses_its_fixed_delta(self):
        expected_scores = {1: 0.05, 2: 0.15, 3: 0.30, 4: 0.50}
        for review_round, expected_score in expected_scores.items():
            review = ReviewSchedule(
                id=f"rev_round_{review_round}", user_id="u1", question_id="q1",
                review_round=review_round, scheduled_date=datetime.utcnow(),
            )
            self.db.add(review)
            self.db.flush()
            apply_review_mastery(self.db, review)
            record = self.db.query(Mastery).filter_by(user_id="u1", node_id="node_a").one()
            self.assertAlmostEqual(record.score, expected_score)

    def test_review_completion_route_does_not_apply_twice(self):
        review = ReviewSchedule(
            id="rev_owned", user_id="u1", question_id="q1", review_round=2,
            scheduled_date=datetime.utcnow() - timedelta(days=1),
        )
        self.db.add(review)
        self.db.commit()

        with patch("backend.routers.review.get_user_id", return_value="u1"):
            complete_review("rev_owned", _Request("u1"), self.db)
            complete_review("rev_owned", _Request("u1"), self.db)

        record = self.db.query(Mastery).filter_by(user_id="u1", node_id="node_a").one()
        self.assertEqual(record.score, 0.1)
        self.assertEqual(record.total_sessions, 1)
        self.assertEqual(record.correct_sessions, 1)

    def test_user_cannot_complete_another_users_review(self):
        review = ReviewSchedule(
            id="rev_other", user_id="u2", question_id="q1", review_round=1,
            scheduled_date=datetime.utcnow() - timedelta(days=1),
        )
        self.db.add(review)
        self.db.commit()

        with patch("backend.routers.review.get_user_id", return_value="u1"):
            with self.assertRaises(HTTPException) as raised:
                complete_review("rev_other", _Request("u1"), self.db)
        self.assertEqual(raised.exception.status_code, 404)

    def test_tutor_completion_schedules_reviews_only_once(self):
        self.question.teaching_json = json.dumps({"teachable_steps": [{
            "step_number": 1,
            "guiding_question": "answer?",
            "expected_answer": "yes",
            "correct_response": "correct",
        }]})
        self.session.steps_json = json.dumps([{"step": 1, "status": "pending", "attempts": 0}])
        self.session.total_steps = 1
        self.db.commit()

        with patch("backend.routers.tutor.get_user_id", return_value="u1"):
            tutor_message(TutorMessageRequest(session_id="s1", message="yes"), _Request("u1"), self.db)
            tutor_message(TutorMessageRequest(session_id="s1", message="yes"), _Request("u1"), self.db)

        self.assertEqual(self.db.query(ReviewSchedule).filter_by(question_id="q1", user_id="u1").count(), 4)
        self.assertEqual(self.db.query(Mastery).filter_by(user_id="u1", node_id="node_a").one().total_sessions, 1)

    def test_tutor_session_and_message_are_scoped_to_current_user(self):
        with patch("backend.routers.tutor.get_user_id", return_value="u2"):
            with self.assertRaises(HTTPException) as create_raised:
                create_session(TutorSessionCreate(question_id="q1"), _Request("u2"), self.db)
            with self.assertRaises(HTTPException) as message_raised:
                tutor_message(TutorMessageRequest(session_id="s1", message="yes"), _Request("u2"), self.db)

        self.assertEqual(create_raised.exception.status_code, 404)
        self.assertEqual(message_raised.exception.status_code, 404)

    def test_two_database_sessions_claim_tutor_mastery_once(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_engine(f"sqlite:///{path}")
        factory = sessionmaker(bind=engine)
        first = second = verify = None
        try:
            Base.metadata.create_all(engine)
            setup = factory()
            setup.add_all([
                User(id="u_concurrent", username="concurrent", name="Student"),
                Question(
                    id="q_concurrent", user_id="u_concurrent", text="question",
                    knowmap_nodes=json.dumps(["node_a"]), status="complete",
                ),
                Session(
                    id="s_concurrent", user_id="u_concurrent", question_id="q_concurrent",
                    status="completed",
                ),
            ])
            setup.commit()
            setup.close()

            first, second = factory(), factory()
            second_question = second.get(Question, "q_concurrent")
            second_session = second.get(Session, "s_concurrent")
            first_update = apply_tutor_mastery(
                first, "u_concurrent", first.get(Question, "q_concurrent"),
                first.get(Session, "s_concurrent"), 0.3,
            )
            if first_update.updated_nodes:
                schedule_reviews("u_concurrent", "q_concurrent", first)
            first.commit()
            second_update = apply_tutor_mastery(
                second, "u_concurrent", second_question, second_session, 0.3,
            )
            second.commit()

            verify = factory()
            mastery = verify.query(Mastery).filter_by(user_id="u_concurrent", node_id="node_a").one()
            self.assertEqual(second_update.updated_nodes, [])
            self.assertEqual(mastery.score, 0.3)
            self.assertEqual(mastery.total_sessions, 1)
            self.assertEqual(verify.query(ReviewSchedule).filter_by(question_id="q_concurrent").count(), 4)
            verify.close()
        finally:
            for db in (verify, first, second):
                if db:
                    db.close()
            engine.dispose()
            os.unlink(path)

    def test_two_database_sessions_claim_review_mastery_once(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_engine(f"sqlite:///{path}")
        factory = sessionmaker(bind=engine)
        first = second = verify = None
        try:
            Base.metadata.create_all(engine)
            setup = factory()
            setup.add_all([
                User(id="u_concurrent", username="concurrent", name="Student"),
                Question(
                    id="q_concurrent", user_id="u_concurrent", text="question",
                    knowmap_nodes=json.dumps(["node_a"]), status="complete",
                ),
                ReviewSchedule(
                    id="rev_concurrent", user_id="u_concurrent", question_id="q_concurrent",
                    review_round=2,
                ),
            ])
            setup.commit()
            setup.close()

            first, second = factory(), factory()
            second_review = second.get(ReviewSchedule, "rev_concurrent")
            apply_review_mastery(first, first.get(ReviewSchedule, "rev_concurrent"))
            first.commit()
            second_update = apply_review_mastery(second, second_review)
            second.commit()

            verify = factory()
            mastery = verify.query(Mastery).filter_by(user_id="u_concurrent", node_id="node_a").one()
            self.assertEqual(second_update.updated_nodes, [])
            self.assertEqual(mastery.score, 0.1)
            self.assertEqual(mastery.total_sessions, 1)
            verify.close()
        finally:
            for db in (verify, first, second):
                if db:
                    db.close()
            engine.dispose()
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
