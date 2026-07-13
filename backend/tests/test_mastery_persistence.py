import json
import os
import tempfile
import threading
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.database import Base, init_db
from backend.models.mastery import Mastery
from backend.models.mastery_change_event import MasteryChangeEvent
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

    def test_tutor_mastery_records_one_change_event_per_updated_node(self):
        self.session.status = "completed"
        self.db.commit()

        apply_tutor_mastery(self.db, "u1", self.question, self.session, 0.3)
        apply_tutor_mastery(self.db, "u1", self.question, self.session, 0.3)

        events = self.db.query(MasteryChangeEvent).filter_by(user_id="u1").all()
        self.assertEqual(len(events), 2)
        self.assertEqual({event.node_id for event in events}, {"node_a", "node_b"})
        self.assertEqual({event.delta for event in events}, {0.3})
        self.assertEqual({event.source for event in events}, {"tutor"})

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

    def test_two_threads_claim_tutor_mastery_once(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
        factory = sessionmaker(bind=engine)
        verify = None
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

            barrier = threading.Barrier(2)
            results, errors = [], []

            def worker():
                db = factory()
                try:
                    question = db.get(Question, "q_concurrent")
                    session = db.get(Session, "s_concurrent")
                    barrier.wait()
                    result = apply_tutor_mastery(db, "u_concurrent", question, session, 0.3)
                    if result.applied:
                        schedule_reviews("u_concurrent", "q_concurrent", db)
                    db.commit()
                    results.append(result.applied)
                except Exception as error:
                    db.rollback()
                    errors.append(error)
                finally:
                    db.close()

            threads = [threading.Thread(target=worker) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            verify = factory()
            mastery = verify.query(Mastery).filter_by(user_id="u_concurrent", node_id="node_a").one()
            self.assertEqual(errors, [])
            self.assertEqual(results.count(True), 1)
            self.assertEqual(mastery.score, 0.3)
            self.assertEqual(mastery.total_sessions, 1)
            self.assertEqual(verify.query(ReviewSchedule).filter_by(question_id="q_concurrent").count(), 4)
            verify.close()
        finally:
            for db in (verify,):
                if db:
                    db.close()
            engine.dispose()
            os.unlink(path)

    def test_two_threads_claim_review_mastery_once(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
        factory = sessionmaker(bind=engine)
        verify = None
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

            barrier = threading.Barrier(2)
            results, errors = [], []

            def worker():
                db = factory()
                try:
                    review = db.get(ReviewSchedule, "rev_concurrent")
                    barrier.wait()
                    result = apply_review_mastery(db, review)
                    db.commit()
                    results.append(result.applied)
                except Exception as error:
                    db.rollback()
                    errors.append(error)
                finally:
                    db.close()

            threads = [threading.Thread(target=worker) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            verify = factory()
            mastery = verify.query(Mastery).filter_by(user_id="u_concurrent", node_id="node_a").one()
            self.assertEqual(errors, [])
            self.assertEqual(results.count(True), 1)
            self.assertEqual(mastery.score, 0.1)
            self.assertEqual(mastery.total_sessions, 1)
            verify.close()
        finally:
            for db in (verify,):
                if db:
                    db.close()
            engine.dispose()
            os.unlink(path)

    def test_init_db_merges_duplicate_legacy_mastery_before_unique_index(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        legacy_engine = create_engine(f"sqlite:///{path}")
        try:
            with legacy_engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE mastery (
                        id VARCHAR PRIMARY KEY, user_id VARCHAR NOT NULL, node_id VARCHAR NOT NULL,
                        score FLOAT, total_sessions INTEGER, correct_sessions INTEGER,
                        variant_passed BOOLEAN, last_reviewed DATETIME, manual_adjustments JSON,
                        created_at DATETIME, updated_at DATETIME
                    )
                """))
                conn.execute(text("""
                    INSERT INTO mastery (id, user_id, node_id, score, total_sessions, correct_sessions, variant_passed, last_reviewed, manual_adjustments)
                    VALUES
                    ('m_a', 'u_legacy', 'node_legacy', 0.4, 2, 1, 0, '2026-01-01 00:00:00', '[{"source":"first"}]'),
                    ('m_b', 'u_legacy', 'node_legacy', 0.8, 3, 2, 1, '2026-02-01 00:00:00', '[{"source":"second"}]')
                """))

            with patch("backend.database.engine", legacy_engine):
                init_db()

            with legacy_engine.connect() as conn:
                rows = conn.execute(text("SELECT * FROM mastery WHERE user_id = 'u_legacy'")).mappings().all()
                indexes = conn.execute(text("PRAGMA index_list(mastery)")).mappings().all()
                tables = {
                    row["name"] for row in conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type = 'table'")
                    ).mappings()
                }
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], "m_a")
            self.assertEqual(rows[0]["score"], 0.8)
            self.assertEqual(rows[0]["total_sessions"], 5)
            self.assertEqual(rows[0]["correct_sessions"], 3)
            self.assertTrue(rows[0]["variant_passed"])
            self.assertEqual(str(rows[0]["last_reviewed"]), "2026-02-01 00:00:00")
            self.assertEqual(
                json.loads(rows[0]["manual_adjustments"]),
                [{"source": "first"}, {"source": "second"}],
            )
            self.assertIn("uq_mastery_user_node", {row["name"] for row in indexes})
            self.assertIn("mastery_change_events", tables)
        finally:
            legacy_engine.dispose()
            os.unlink(path)

    def test_two_completed_sessions_update_one_mastery_node_concurrently(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
        factory = sessionmaker(bind=engine)
        verify = None
        try:
            Base.metadata.create_all(engine)
            setup = factory()
            setup.add_all([
                User(id="u_parallel", username="parallel", name="Student"),
                Question(id="q_parallel_1", user_id="u_parallel", text="q1", knowmap_nodes=json.dumps(["node_a"])),
                Question(id="q_parallel_2", user_id="u_parallel", text="q2", knowmap_nodes=json.dumps(["node_a"])),
                Session(id="s_parallel_1", user_id="u_parallel", question_id="q_parallel_1", status="completed"),
                Session(id="s_parallel_2", user_id="u_parallel", question_id="q_parallel_2", status="completed"),
            ])
            setup.commit()
            setup.close()

            barrier = threading.Barrier(2)
            results, errors = [], []

            def worker(question_id, session_id):
                db = factory()
                try:
                    question = db.get(Question, question_id)
                    session = db.get(Session, session_id)
                    barrier.wait()
                    result = apply_tutor_mastery(db, "u_parallel", question, session, 0.3)
                    db.commit()
                    results.append(result.applied)
                except Exception as error:
                    db.rollback()
                    errors.append(error)
                finally:
                    db.close()

            threads = [
                threading.Thread(target=worker, args=("q_parallel_1", "s_parallel_1")),
                threading.Thread(target=worker, args=("q_parallel_2", "s_parallel_2")),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            verify = factory()
            mastery = verify.query(Mastery).filter_by(user_id="u_parallel", node_id="node_a").one()
            self.assertEqual(errors, [])
            self.assertEqual(results.count(True), 2)
            self.assertAlmostEqual(mastery.score, 0.6)
            self.assertEqual(mastery.total_sessions, 2)
            self.assertEqual(mastery.correct_sessions, 2)
        finally:
            if verify:
                verify.close()
            engine.dispose()
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
