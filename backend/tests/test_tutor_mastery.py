"""Tests for tutor session completion mastery accounting.

Pins P0-TUTOR-01 / -03 fixes so a session that finishes with zero or
low correct steps no longer reports ``mastery_achieved`` or ``+0.3``.
"""

import json
import unittest
from types import SimpleNamespace

from backend.services.tutor_engine import process_message, _check_answer


def _make_session():
    return SimpleNamespace(
        current_step=0,
        steps_json=None,
        messages_json=json.dumps([]),
        mistakes_json=json.dumps([]),
        diagnostic_json=None,
        hints_used=0,
        status="in_progress",
        mastery_achieved=False,
        total_steps=0,
    )


def _teach(*expected_answers):
    steps = []
    for i, expected in enumerate(expected_answers, start=1):
        steps.append({
            "step_number": i,
            "guiding_question": f"第{i}步做什么",
            "expected_answer": expected,
            "correct_response": "正确！",
            "wrong_response": "再想想。",
            "hint": "提示。",
            "stuck_response": "这一步应当：",
        })
    return steps


def _init_steps(session, teaching):
    session.total_steps = len(teaching)
    session.steps_json = json.dumps([
        {"step": s["step_number"], "status": "pending", "attempts": 0}
        for s in teaching
    ])


class CheckAnswerTest(unittest.TestCase):
    def test_empty_expected_answer_is_not_auto_correct(self):
        self.assertFalse(_check_answer("任意输入", ""))
        self.assertFalse(_check_answer("", ""))

    def test_matches_when_expected_keyword_present(self):
        self.assertTrue(_check_answer("答案是 x=1", "x=1"))


class MasteryCompletionTest(unittest.TestCase):
    def test_all_wrong_completion_reports_no_mastery(self):
        session = _make_session()
        teaching = _teach("x=1")
        _init_steps(session, teaching)

        for _ in range(3):
            result = process_message(session, "不会", "answer", teaching, None)

        self.assertEqual(result["type"], "complete")
        self.assertFalse(session.mastery_achieved)
        self.assertEqual(result["mastery_update"], 0.0)
        self.assertEqual(result["diagnostic_summary"]["completed_steps"], 0)
        self.assertNotIn("掌握", result["reply"])

    def test_all_correct_completion_reports_mastery(self):
        session = _make_session()
        teaching = _teach("x=1", "y=2")
        _init_steps(session, teaching)

        r1 = process_message(session, "x=1", "answer", teaching, None)
        self.assertEqual(r1["type"], "correct")
        r2 = process_message(session, "y=2", "answer", teaching, None)

        self.assertEqual(r2["type"], "complete")
        self.assertTrue(session.mastery_achieved)
        self.assertEqual(r2["mastery_update"], 0.3)
        self.assertEqual(r2["diagnostic_summary"]["completed_steps"], 2)

    def test_partial_completion_gives_partial_credit_without_mastery(self):
        session = _make_session()
        teaching = _teach("x=1", "y=2", "z=3")
        _init_steps(session, teaching)

        process_message(session, "x=1", "answer", teaching, None)
        process_message(session, "y=2", "answer", teaching, None)
        for _ in range(3):
            result = process_message(session, "不会", "answer", teaching, None)

        self.assertEqual(result["type"], "complete")
        self.assertFalse(session.mastery_achieved)
        self.assertEqual(result["mastery_update"], 0.1)
        self.assertEqual(result["diagnostic_summary"]["completed_steps"], 2)


if __name__ == "__main__":
    unittest.main()