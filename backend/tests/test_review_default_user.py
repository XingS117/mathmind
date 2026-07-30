"""P1-REVIEW-01: default (unauthenticated) user must be able to see
their own scheduled reviews.
"""

import unittest
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import app
from backend.models.review import ReviewSchedule


class DefaultUserReviewsTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self._marker = f"test_{uuid.uuid4().hex[:8]}"
        past = datetime.utcnow() - timedelta(days=1)
        future = datetime.utcnow() + timedelta(seconds=30)
        for scheduled, tag in ((past, "upcoming"), (future, "future")):
            self.db.add(
                ReviewSchedule(
                    id=f"rev_{self._marker}_{tag}",
                    user_id="u_default",
                    question_id=f"q_{self._marker}",
                    review_round=1,
                    review_type="quick",
                    scheduled_date=scheduled,
                )
            )
        self.db.commit()

    def tearDown(self):
        self.db.query(ReviewSchedule).filter(
            ReviewSchedule.id.like(f"rev_{self._marker}_%")
        ).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_default_user_sees_own_reviews(self):
        r = self.client.get("/api/v1/learn/reviews")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        upcoming_ids = {u["id"] for u in data.get("upcoming", [])}
        future_ids = {u["id"] for u in data.get("future", [])}
        self.assertIn(f"rev_{self._marker}_upcoming", upcoming_ids)
        self.assertIn(f"rev_{self._marker}_future", future_ids)


if __name__ == "__main__":
    unittest.main()
