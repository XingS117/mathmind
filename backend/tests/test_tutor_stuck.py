"""P1-TUTOR-04: 3-attempts stuck walk-through must not duplicate the
expected answer.
"""

import json
import unittest
from types import SimpleNamespace

from backend.services.tutor_engine import process_message, _stuck_reply


def _make_session():
    return SimpleNamespace(
        current_step=0,
        steps_json=json.dumps([
            {"step": 1, "status": "pending", "attempts": 0},
            {"step": 2, "status": "pending", "attempts": 0},
        ]),
        messages_json=json.dumps([]),
        mistakes_json=json.dumps([]),
        diagnostic_json=None,
        hints_used=0,
        status="in_progress",
        mastery_achieved=False,
        total_steps=2,
    )


class StuckReplyTest(unittest.TestCase):
    def test_identical_stuck_and_expected_not_duplicated(self):
        step = {"stuck_response": "AB=10, AE=12", "expected_answer": "AB=10, AE=12"}
        self.assertEqual(_stuck_reply(step), "AB=10, AE=12")

    def test_stuck_containing_expected_not_duplicated(self):
        step = {"stuck_response": "答案是 AB=10, AE=12。", "expected_answer": "AB=10, AE=12"}
        self.assertEqual(_stuck_reply(step), "答案是 AB=10, AE=12。")

    def test_different_stuck_and_expected_are_joined_once(self):
        step = {"stuck_response": "先列比例式：", "expected_answer": "x=1"}
        got = _stuck_reply(step)
        self.assertEqual(got.count("x=1"), 1)
        self.assertIn("先列比例式", got)

    def test_missing_stuck_falls_back_to_lead_in(self):
        self.assertEqual(_stuck_reply({"expected_answer": "x=1"}), "我们一起来做：x=1")

    def test_all_empty_returns_default(self):
        self.assertEqual(_stuck_reply({}), "我们一起来做这一步。")


class StuckIntegrationTest(unittest.TestCase):
    def test_3rd_wrong_attempt_walk_through_no_duplicate(self):
        session = _make_session()
        teaching = [
            {
                "step_number": 1,
                "guiding_question": "第1步做什么",
                "expected_answer": "AB=10, AE=12",
                "correct_response": "对！",
                "wrong_response": "再想想",
                "hint": "先看题干",
                "stuck_response": "AB=10, AE=12",
            },
            {
                "step_number": 2,
                "guiding_question": "第2步做什么",
                "expected_answer": "x=2",
                "correct_response": "对！",
                "wrong_response": "再想想",
                "hint": "代入",
                "stuck_response": "x=2",
            },
        ]
        for _ in range(3):
            r = process_message(session, "不会", "answer", teaching, None)
        self.assertEqual(r["reply"].count("AB=10, AE=12"), 1)


if __name__ == "__main__":
    unittest.main()
