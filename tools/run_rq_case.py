"""Run one RQ case end-to-end via the running backend and print an
evidence bundle suitable for pasting into ``docs/quality/cases/RQ-*.md``.

Assumes ``uvicorn`` is up on ``http://127.0.0.1:8000`` with PaddleOCR
ready and DeepSeek/LLM configured under ``u_admin``.
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = os.environ.get("MATHMIND_BASE", "http://127.0.0.1:8000")
CASES_PATH = Path(__file__).resolve().parents[1] / "data" / "acceptance" / "real-question-cases.json"


def load_case(case_id: str) -> dict:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    for c in cases:
        if c["case_id"] == case_id:
            return c
    raise SystemExit(f"case {case_id} not found")


def analyze(case: dict) -> dict:
    files = []
    for img in case["images"]:
        p = Path(img["path"])
        if not p.exists():
            raise SystemExit(f"missing image {p}")
        files.append(("image", (p.name, p.read_bytes(), "image/jpeg")))
    r = requests.post(f"{BASE}/api/v1/questions/analyze", files=files, timeout=600)
    r.raise_for_status()
    return r.json()


def confirm(analysis: dict) -> dict:
    payload = {
        "text": analysis.get("text", ""),
        "question_type": analysis.get("question_type", "计算题"),
        "difficulty": analysis.get("difficulty", 2),
        "knowledge_points": analysis.get("knowledge_points", []),
        "has_diagram": analysis.get("has_diagram", False),
        "raw_ocr_text": analysis.get("raw_ocr_text", ""),
        "final_answer": "",
        "solution_text": "",
        "key_insight": analysis.get("key_insight", ""),
        "knowmap_nodes": analysis.get("suggested_nodes", [])[:2],
        "analysis_source": analysis.get("source", "ocr"),
        "analysis_confidence": analysis.get("confidence", 0),
        "needs_human_review": False,
    }
    r = requests.post(
        f"{BASE}/api/v1/questions/confirm",
        json=payload,
        timeout=180,
    )
    r.raise_for_status()
    return r.json()


def create_session(qid: str) -> dict:
    r = requests.post(
        f"{BASE}/api/v1/tutor/session",
        json={"question_id": qid},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def send_msg(sid: str, msg: str, intent: str = "answer") -> dict:
    r = requests.post(
        f"{BASE}/api/v1/tutor/message",
        json={"session_id": sid, "message": msg, "intent": intent},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def tutor_walkthrough(session: dict) -> list[dict]:
    """Exercise every branch: 1 wrong, 1 hint, then walk answers to end
    always wrong so we reach a stuck/complete flow.
    """
    sid = session["session_id"]
    total = session["total_steps"]
    log = []
    # 1) wrong on step 1
    log.append({"branch": "wrong-1", "resp": send_msg(sid, "不知道", "answer")})
    # 2) hint on step 1
    log.append({"branch": "hint-1", "resp": send_msg(sid, "?", "hint")})
    # 3) walk remaining answers wrong until complete
    for i in range(total * 3 + 3):
        r = send_msg(sid, "??", "answer")
        log.append({"branch": f"answer-{i}", "resp": r})
        if r["type"] == "complete":
            break
    return log


def run(case_id: str) -> None:
    case = load_case(case_id)
    print(f"=== {case_id}: {case['title']} ===\n")

    t0 = time.time()
    analysis = analyze(case)
    print(f"[analyze] took {time.time()-t0:.1f}s  success={analysis.get('success')}  confidence={analysis.get('confidence')}")
    print(f"  question_type: {analysis.get('question_type')}")
    print(f"  knowledge_points: {analysis.get('knowledge_points')}")
    print(f"  suggested_nodes: {analysis.get('suggested_nodes')}")
    print(f"  raw_ocr_text (first 200): {(analysis.get('raw_ocr_text') or '')[:200]}")
    print(f"  key_insight: {(analysis.get('key_insight') or '')[:200]}")
    print(f"  text (first 200): {(analysis.get('text') or '')[:200]}")
    print()

    if not analysis.get("success"):
        print("STOP: analyze failed")
        return

    t0 = time.time()
    conf = confirm(analysis)
    print(f"[confirm] took {time.time()-t0:.1f}s  question_id={conf['question_id']}")
    qid = conf["question_id"]

    sess = create_session(qid)
    print(f"[session] session_id={sess['session_id']}  total_steps={sess['total_steps']}  confidence={sess.get('solution_confidence')}  uncertain={sess.get('uncertain_points')}")
    print()

    log = tutor_walkthrough(sess)
    for entry in log[-4:]:
        r = entry["resp"]
        reply_head = r["reply"][:120].replace("\n", " ")
        print(f"  [{entry['branch']}] type={r['type']}  step={r['step_index']}/{r['total_steps']}  reply={reply_head}")
    last = log[-1]["resp"]
    print()
    print(f"[complete] mastery_update={last.get('mastery_update')}  diag={last.get('diagnostic_summary')}")


if __name__ == "__main__":
    for cid in sys.argv[1:]:
        run(cid)
        print("\n" + "=" * 60 + "\n")
