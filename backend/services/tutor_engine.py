import random

ENCOURAGE_CORRECT = ['做得好！', '不错！', '对了！', '很棒！', '完全正确！']
ENCOURAGE_WRONG = ['再想想？', '差一点！', '换个思路试试', '注意细节哦', '接近了！']
ENCOURAGE_COMPLETE = ['太棒了！这道题你已经掌握了！', '完成得很好！知识点又固惆了一遍', '厉害！继续挑战下一题吧']
import json, logging
from typing import Optional
from sqlalchemy.orm import Session as DBSession
from backend.models.session import Session

logger = logging.getLogger(__name__)

def build_diagnostic_summary(
    steps: list[dict],
    teaching_steps: list[dict],
    mistakes: list[str],
    hints_used: int
) -> dict:
    """Build a compact learning summary for the completed tutoring session."""
    total_steps = len(teaching_steps)
    completed_steps = sum(1 for s in steps if s.get("status") == "correct")
    stuck_steps = [
        i + 1 for i, s in enumerate(steps)
        if int(s.get("attempts") or 0) >= 3
    ]
    weak_spots = _infer_weak_spots(mistakes, stuck_steps, teaching_steps)
    next_action = _next_action(stuck_steps, weak_spots, teaching_steps)

    return {
        "completed_steps": completed_steps,
        "total_steps": total_steps,
        "hints_used": hints_used,
        "stuck_steps": stuck_steps,
        "weak_spots": weak_spots,
        "next_action": next_action,
    }

def _infer_weak_spots(mistakes: list[str], stuck_steps: list[int], teaching_steps: list[dict]) -> list[str]:
    spots: list[str] = []
    joined = " ".join(mistakes)
    if any(word in joined for word in ["方程", "列式", "关系"]):
        spots.append("列方程")
    if any(word in joined for word in ["算错", "计算", "符号"]):
        spots.append("计算细节")
    if any(word in joined for word in ["不会", "不懂", "没思路"]):
        spots.append("思路启动")
    for step_no in stuck_steps:
        idx = step_no - 1
        question = teaching_steps[idx].get("guiding_question", "") if idx < len(teaching_steps) else ""
        if question and question not in spots:
            spots.append(question)
    return spots[:3] or ["本题关键步骤"]

def _next_action(stuck_steps: list[int], weak_spots: list[str], teaching_steps: list[dict]) -> str:
    if stuck_steps:
        step_no = stuck_steps[0]
        idx = step_no - 1
        question = teaching_steps[idx].get("guiding_question", "") if idx < len(teaching_steps) else ""
        return f"回看第{step_no}步：{question or '重新梳理解题关键'}"
    if weak_spots:
        return f"复习：{weak_spots[0]}"
    return "尝试一道同知识点变式题"

def start_session(session: Session, teaching_steps: list[dict]):
    """Initialize a new tutoring session."""
    session.total_steps = len(teaching_steps)
    session.current_step = 0
    session.steps_json = json.dumps([
        {"step": s.get("step_number", i+1), "status": "pending", "attempts": 0}
        for i, s in enumerate(teaching_steps)
    ])
    session.messages_json = json.dumps([])
    session.hints_used = 0
    session.mistakes_json = json.dumps([])

def process_message(
    session: Session,
    user_message: str,
    intent: str,
    teaching_steps: list[dict],
    db: DBSession
) -> dict:
    """Process a student message and return tutor response."""

    current = session.current_step
    steps = json.loads(session.steps_json) if isinstance(session.steps_json, str) else (session.steps_json or [])
    messages = json.loads(session.messages_json) if isinstance(session.messages_json, str) else (session.messages_json or [])
    mistakes = json.loads(session.mistakes_json) if isinstance(session.mistakes_json, str) else (session.mistakes_json or [])

    # Save user message
    messages.append({"role": "user", "content": user_message, "intent": intent})
    hints_remaining = max(0, 3 - session.hints_used)

    # Out of bounds check
    if current >= len(teaching_steps):
        return _complete(session, steps, messages, hints_remaining, teaching_steps)

    step_data = teaching_steps[current]
    step_state = steps[current] if current < len(steps) else {"status": "pending", "attempts": 0}

    if intent == "hint":
        session.hints_used += 1
        hint = _short_hint(step_data)
        hints_remaining = max(0, 3 - session.hints_used)
        reply = f"提示：{hint}"
        messages.append({"role": "system", "content": reply})
        session.messages_json = json.dumps(messages)
        return {
            "type": "hint", "reply": reply,
            "step_index": current + 1, "total_steps": len(teaching_steps),
            "hints_remaining": hints_remaining, "mastery_update": None,
            "variant_suggested": None
        }

    elif intent == "detail":
        detail = step_data.get("detail_level", {})
        detail_text = detail.get("advanced", step_data.get("description", ""))
        reply = f"详细讲解：{detail_text}"
        messages.append({"role": "system", "content": reply})
        session.messages_json = json.dumps(messages)
        return {
            "type": "continue", "reply": reply,
            "step_index": current + 1, "total_steps": len(teaching_steps),
            "hints_remaining": hints_remaining, "mastery_update": None,
            "variant_suggested": None
        }

    elif intent == "skip":
        messages.append({"role": "system", "content": f"第{current+1}步跳过。下面进入下一步。"})
        return _advance(session, steps, messages, teaching_steps, current + 1, hints_remaining)

    # Default: answer evaluation
    expected = step_data.get("expected_answer", "").lower().strip()
    user_lower = user_message.lower().strip()

    # Simple keyword matching for Mock mode
    is_correct = _check_answer(user_lower, expected)

    if is_correct:
        step_state["status"] = "correct"
        step_state["attempts"] += 1
        steps[current] = step_state
        session.steps_json = json.dumps(steps)

        reply = random.choice(ENCOURAGE_CORRECT) + " " + step_data.get("correct_response", "正确！")
        has_next = current + 1 < len(teaching_steps)
        if has_next:
            next_step = teaching_steps[current + 1]
            reply += " " + next_step.get("guiding_question", "下一步怎么做？")
            messages.append({"role": "system", "content": reply})
            session.messages_json = json.dumps(messages)
            session.current_step = current + 1
            return {
                "type": "correct", "reply": reply,
                "step_index": current + 2, "total_steps": len(teaching_steps),
                "hints_remaining": hints_remaining, "mastery_update": None,
                "variant_suggested": None
            }
        else:
            return _complete(session, steps, messages, hints_remaining, teaching_steps)
    else:
        step_state["attempts"] += 1
        if step_state["attempts"] >= 3:
            reply = _stuck_reply(step_data)
            return _advance(session, steps, messages, teaching_steps, current + 1, hints_remaining, reply)
        else:
            reply = random.choice(ENCOURAGE_WRONG) + " " + step_data.get("wrong_response", "再想想？")
            if step_state["attempts"] >= 2:
                reply += f" 提示：{step_data.get('hint', '')}"
            if user_lower not in mistakes:
                mistakes.append(user_lower)
            session.mistakes_json = json.dumps(mistakes)
            steps[current] = step_state
            session.steps_json = json.dumps(steps)
            messages.append({"role": "system", "content": reply})
            session.messages_json = json.dumps(messages)
            return {
                "type": "wrong", "reply": reply,
                "step_index": current + 1, "total_steps": len(teaching_steps),
                "hints_remaining": hints_remaining, "mastery_update": None,
                "variant_suggested": None
            }

def _check_answer(user_answer: str, expected: str) -> bool:
    """Simple keyword-based answer checking for Mock mode.

    When ``expected`` is empty we deliberately return ``False``: an empty
    reference answer must not silently mark any student input as correct
    (P0-TUTOR-01). The 3-attempt stuck flow still hands the step over with
    the teaching explanation.
    """
    if not expected:
        return False
    expected_keywords = expected.replace("？", "").replace("?", "").split()
    return any(kw in user_answer for kw in expected_keywords)

_MAX_HINT_CHARS = 40


def _short_hint(step_data: dict) -> str:
    """Return a *short* nudge for the ``hint`` intent (P1-HINT-01).

    Historically ``hint`` returned ``step_data["hint"]`` verbatim, but
    upload.py fills that field with the full step description (100+
    Chinese characters) — that is the entire solution, so returning it
    is textbook leakage.

    We now derive a hint that:
    - prefers ``guiding_question`` (an open-ended prompt);
    - falls back to the first sentence of ``hint``/``description`` and
      never exceeds ``_MAX_HINT_CHARS`` visible characters;
    - never returns the full expected answer even if the caller stuffed
      it into ``hint``.
    """
    guiding = str(step_data.get("guiding_question") or "").strip()
    if guiding:
        return _truncate_hint(guiding)
    raw = str(step_data.get("hint") or step_data.get("description") or "").strip()
    if not raw:
        return "再想想？"
    expected = str(step_data.get("expected_answer") or "").strip()
    if expected and expected in raw:
        # If someone (LLM/prompt bug) put the full answer inside hint,
        # drop the answer portion so we don't leak it.
        raw = raw.split(expected, 1)[0].strip() or raw
    return _truncate_hint(raw)


def _truncate_hint(text: str) -> str:
    text = text.strip()
    if len(text) <= _MAX_HINT_CHARS:
        return text
    # Try to cut at the first sentence boundary within the budget.
    for i, ch in enumerate(text[:_MAX_HINT_CHARS]):
        if ch in "。！？!?；;\n":
            return text[: i + 1]
    return text[:_MAX_HINT_CHARS].rstrip() + "…"


def _stuck_reply(step_data: dict) -> str:
    """Compose the 3-attempts walk-through reply without duplicating the
    expected answer (P1-TUTOR-04).

    ``upload.py`` populates ``stuck_response`` with the step ``result``,
    which is the same string as ``expected_answer``. The old code just
    concatenated the two, producing outputs like ``AB=10, AE=12AB=10,
    AE=12``. We now emit a single copy: prefer a non-empty
    ``stuck_response`` alone, otherwise fall back to a lead-in phrase
    plus ``expected_answer``.
    """
    stuck = str(step_data.get("stuck_response") or "").strip()
    expected = str(step_data.get("expected_answer") or "").strip()
    if stuck and expected and stuck != expected and expected not in stuck:
        return f"{stuck}{expected}"
    if stuck:
        return stuck
    if expected:
        return f"我们一起来做：{expected}"
    return "我们一起来做这一步。"

def _advance(session, steps, messages, teaching_steps, next_step, hints_remaining, reply_override=None):
    """Advance to the next step."""
    if next_step >= len(teaching_steps):
        return _complete(session, steps, messages, hints_remaining, teaching_steps)
    next_s = teaching_steps[next_step]
    reply = reply_override or next_s.get("guiding_question", "下一步怎么做？")
    messages.append({"role": "system", "content": reply})
    session.messages_json = json.dumps(messages)
    session.current_step = next_step
    return {
        "type": "continue", "reply": reply,
        "step_index": next_step + 1, "total_steps": len(teaching_steps),
        "hints_remaining": hints_remaining, "mastery_update": None,
        "variant_suggested": None
    }

def _complete(session, steps, messages, hints_remaining, teaching_steps):
    """Complete the tutoring session.

    Mastery accounting (P0-TUTOR-03): a session that finished because the
    student was walked through every step but got nothing right must not
    report ``mastery_achieved`` nor award the full ``+0.3`` mastery delta.
    Both are derived from the ratio of correctly answered steps.
    """
    total = len(teaching_steps)
    completed = sum(1 for s in steps if s.get("status") == "correct")
    ratio = (completed / total) if total else 0.0

    if total > 0 and completed == total:
        mastery_achieved = True
        mastery_update = 0.3
        reply = "很好！你已经完成了这道题的学习。需要做一道类似的题巩固一下吗？"
    elif ratio >= 0.6:
        mastery_achieved = False
        mastery_update = 0.1
        reply = (
            f"这道题走完了，答对 {completed}/{total} 步，还没完全掌握。"
            "先回看卡住的步骤，我们下次再练一遍。"
        )
    else:
        mastery_achieved = False
        mastery_update = 0.0
        reply = (
            f"这道题走完了，答对 {completed}/{total} 步。"
            "先别急着做变式，回到卡住的步骤把讲解看懂再来。"
        )

    session.status = "completed"
    session.mastery_achieved = mastery_achieved
    messages.append({"role": "system", "content": reply})
    session.messages_json = json.dumps(messages)
    mistakes = json.loads(session.mistakes_json) if isinstance(session.mistakes_json, str) else (session.mistakes_json or [])
    diagnostic = build_diagnostic_summary(
        steps=steps,
        teaching_steps=teaching_steps,
        mistakes=mistakes,
        hints_used=session.hints_used,
    )
    session.diagnostic_json = json.dumps(diagnostic)
    return {
        "type": "complete", "reply": reply,
        "step_index": total, "total_steps": total,
        "hints_remaining": hints_remaining,
        "mastery_update": mastery_update,
        "variant_suggested": "需要生成变式题吗？" if mastery_achieved else None,
        "feynman_available": mastery_achieved,
        "reviews_scheduled": True,
        "diagnostic_summary": diagnostic
    }
