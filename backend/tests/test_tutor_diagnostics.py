import json
import unittest
from types import SimpleNamespace

from backend.services.tutor_engine import build_diagnostic_summary, process_message


class TutorDiagnosticSummaryTest(unittest.TestCase):
    def test_summary_marks_stuck_steps_and_next_action(self):
        steps = [
            {"step": 1, "status": "correct", "attempts": 1},
            {"step": 2, "status": "correct", "attempts": 3},
            {"step": 3, "status": "pending", "attempts": 0},
        ]
        teaching_steps = [
            {"guiding_question": "先找等量关系"},
            {"guiding_question": "再列方程"},
            {"guiding_question": "最后求解"},
        ]

        summary = build_diagnostic_summary(
            steps=steps,
            teaching_steps=teaching_steps,
            mistakes=["不会列方程"],
            hints_used=2,
        )

        self.assertEqual(summary["completed_steps"], 2)
        self.assertEqual(summary["total_steps"], 3)
        self.assertEqual(summary["hints_used"], 2)
        self.assertEqual(summary["stuck_steps"], [2])
        self.assertIn("列方程", summary["weak_spots"])
        self.assertEqual(summary["next_action"], "回看第2步：再列方程")

    def test_process_message_records_step_as_stuck_after_three_wrong_attempts(self):
        session = SimpleNamespace(
            current_step=0,
            steps_json=json.dumps([{"step": 1, "status": "pending", "attempts": 0}]),
            messages_json=json.dumps([]),
            mistakes_json=json.dumps([]),
            diagnostic_json=None,
            hints_used=0,
            status="in_progress",
            mastery_achieved=False,
        )
        teaching_steps = [{
            "step_number": 1,
            "guiding_question": "先列方程",
            "expected_answer": "x=1",
            "wrong_response": "检查等量关系。",
            "stuck_response": "这一步要先设未知数。",
        }]

        process_message(session, "不会", "answer", teaching_steps, None)
        process_message(session, "还是不会", "answer", teaching_steps, None)
        result = process_message(session, "乱写", "answer", teaching_steps, None)

        self.assertEqual(result["type"], "complete")
        self.assertEqual(result["diagnostic_summary"]["stuck_steps"], [1])
        self.assertEqual(result["diagnostic_summary"]["next_action"], "回看第1步：先列方程")
        saved = json.loads(session.diagnostic_json)
        self.assertEqual(saved["stuck_steps"], [1])
        self.assertIn("思路启动", saved["weak_spots"])


if __name__ == "__main__":
    unittest.main()
