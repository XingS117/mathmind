"""P1-HINT-01: hint intent must not leak the full step solution."""

import json
import unittest
from types import SimpleNamespace

from backend.services.tutor_engine import process_message, _short_hint


def _make_session():
    return SimpleNamespace(
        current_step=0,
        steps_json=json.dumps([{"step": 1, "status": "pending", "attempts": 0}]),
        messages_json=json.dumps([]),
        mistakes_json=json.dumps([]),
        diagnostic_json=None,
        hints_used=0,
        status="in_progress",
        mastery_achieved=False,
        total_steps=1,
    )


class ShortHintTest(unittest.TestCase):
    def test_prefers_guiding_question(self):
        step = {
            "guiding_question": "第一步做什么？",
            "hint": "先用两点间距离公式列 PA=PC，然后代入求 a" * 10,
            "description": "整整一大段讲解…" * 20,
            "expected_answer": "a=1/2",
        }
        self.assertEqual(_short_hint(step), "第一步做什么？")

    def test_truncates_long_hint(self):
        step = {
            "hint": ("这是一段" * 40).strip(),  # 160 chars
        }
        self.assertLessEqual(len(_short_hint(step)), 41)

    def test_strips_expected_answer_from_hint(self):
        step = {
            "hint": "先列方程 x=1，因为已知条件…",
            "expected_answer": "x=1",
        }
        got = _short_hint(step)
        self.assertNotIn("x=1", got)

    def test_falls_back_to_description(self):
        step = {"description": "这里描述解题思路。"}
        self.assertEqual(_short_hint(step), "这里描述解题思路。")

    def test_empty_returns_default(self):
        self.assertEqual(_short_hint({}), "再想想？")


class HintIntentDoesNotLeakTest(unittest.TestCase):
    def test_hint_intent_reply_is_short(self):
        session = _make_session()
        teaching = [{
            "step_number": 1,
            "guiding_question": "找出 AB 的中点。",
            "hint": "作辅助线，取 AC 中点 F，" * 20,
            "expected_answer": "取 AC 中点 F",
            "correct_response": "对！",
            "wrong_response": "再想想。",
            "stuck_response": "答案是取 AC 中点 F。",
        }]
        r = process_message(session, "?", "hint", teaching, None)
        self.assertEqual(r["type"], "hint")
        # The reply is "提示：<hint>", so trimming the prefix leaves the
        # hint itself, which must be short.
        body = r["reply"].split("：", 1)[-1]
        self.assertLessEqual(len(body), 41)
        self.assertNotIn("expected_answer", r["reply"])


if __name__ == "__main__":
    unittest.main()
