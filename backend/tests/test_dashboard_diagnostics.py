import json
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.mastery_change_event import MasteryChangeEvent
from backend.models.mastery import Mastery
from backend.models.question import Question
from backend.models.review import ReviewSchedule
from backend.models.user import User
from backend.routers.learn import _recent_diagnostic_weak_points, dashboard


class DashboardDiagnosticsTest(unittest.TestCase):
    def test_recent_diagnostic_weak_points_are_deduped_in_order(self):
        sessions = [
            SimpleNamespace(diagnostic_json=json.dumps({"weak_spots": ["思路启动", "计算细节"]})),
            SimpleNamespace(diagnostic_json=json.dumps({"weak_spots": ["思路启动", "列方程"]})),
            SimpleNamespace(diagnostic_json=None),
        ]

        self.assertEqual(
            _recent_diagnostic_weak_points(sessions, limit=3),
            ["思路启动", "计算细节", "列方程"],
        )

    def test_generic_weak_point_uses_question_graph_node_name(self):
        sessions = [
            SimpleNamespace(
                question_id="q1",
                diagnostic_json=json.dumps({"weak_spots": ["本题关键步骤"]}),
            )
        ]
        questions = {
            "q1": SimpleNamespace(knowmap_nodes=json.dumps(["bx1_c3_s1"]), knowledge_points=json.dumps(["一次函数"]))
        }

        result = _recent_diagnostic_weak_points(
            sessions,
            q_map=questions,
            node_lookup=lambda node_id: {"name": "3.1 函数的概念及其表示"} if node_id == "bx1_c3_s1" else None,
            limit=3,
        )

        self.assertEqual(result, ["3.1 函数的概念及其表示"])


class DashboardLearningLoopTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        now = datetime.utcnow()
        self.db.add_all([
            User(id="u1", username="u1", name="Student 1"),
            User(id="u2", username="u2", name="Student 2"),
            Question(id="q1", user_id="u1", text="我的复习题", status="complete"),
            Question(id="q2", user_id="u2", text="别人的复习题", status="complete"),
            ReviewSchedule(id="rev_due", user_id="u1", question_id="q1", review_round=1,
                           review_type="quick", scheduled_date=now - timedelta(days=1)),
            ReviewSchedule(id="rev_second", user_id="u1", question_id="q1", review_round=2,
                           review_type="variant", scheduled_date=now - timedelta(hours=1)),
            ReviewSchedule(id="rev_third", user_id="u1", question_id="q1", review_round=3,
                           review_type="comprehensive", scheduled_date=now),
            ReviewSchedule(id="rev_hidden", user_id="u2", question_id="q2", review_round=1,
                           review_type="quick", scheduled_date=now - timedelta(days=2)),
            Mastery(id="m_recent", user_id="u1", node_id="node_recent", score=0.8,
                    last_reviewed=now - timedelta(days=2)),
            Mastery(id="m_old", user_id="u1", node_id="node_old", score=0.8,
                    last_reviewed=now - timedelta(days=8)),
            Mastery(id="m_other", user_id="u2", node_id="node_other", score=0.9,
                    last_reviewed=now - timedelta(days=1)),
            MasteryChangeEvent(id="event_recent", user_id="u1", node_id="node_recent", delta=0.3,
                               source="tutor", occurred_at=now - timedelta(days=2)),
            MasteryChangeEvent(id="event_old", user_id="u1", node_id="node_old", delta=0.4,
                               source="review", occurred_at=now - timedelta(days=8)),
            MasteryChangeEvent(id="event_other", user_id="u2", node_id="node_other", delta=0.9,
                               source="review", occurred_at=now - timedelta(days=1)),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_dashboard_returns_due_reviews_and_recent_mastery_change(self):
        with patch("backend.routers.learn.get_user_id", return_value="u1"):
            payload = dashboard(SimpleNamespace(headers={}), self.db)

        self.assertEqual([review["id"] for review in payload.due_reviews], ["rev_due", "rev_second", "rev_third"])
        self.assertEqual(payload.due_reviews[0]["question_id"], "q1")
        self.assertEqual(payload.mastery_change, 0.3)

    def test_dashboard_ignores_historical_mastery_without_change_events(self):
        self.db.query(MasteryChangeEvent).delete()
        self.db.commit()

        with patch("backend.routers.learn.get_user_id", return_value="u1"):
            payload = dashboard(SimpleNamespace(headers={}), self.db)

        self.assertEqual(payload.mastery_change, 0.0)


if __name__ == "__main__":
    unittest.main()
