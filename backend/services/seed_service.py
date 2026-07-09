import json, os, logging
from sqlalchemy.orm import Session as DBSession
from backend.models.question import Question

logger = logging.getLogger(__name__)
_seed_questions = []


def load_seed():
    """Load seed questions JSON into memory (used only when explicitly enabled)."""
    global _seed_questions
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "seed_questions.json")
    if not os.path.exists(p):
        logger.warning(f"Seed file not found: {p}")
        return
    with open(p, encoding="utf-8") as f:
        _seed_questions = json.load(f)
    logger.info(f"Loaded {len(_seed_questions)} seed questions")


def _add_question(db, sq):
    q = Question(
        id=sq["id"], user_id="u_default", source="seed",
        source_label=sq.get("source_label", "好题"),
        text=sq["text"], question_type=sq.get("question_type", "计算题"),
        difficulty=sq.get("difficulty", 1),
        knowledge_points=json.dumps(sq.get("knowledge_points", [])),
        knowmap_nodes=json.dumps(sq.get("knowmap_nodes", [])),
        final_answer=sq.get("final_answer", ""),
        has_diagram=sq.get("has_diagram", False),
        diagram_json=json.dumps(sq.get("diagram_json")) if sq.get("has_diagram") else None,
        solution_json=json.dumps(sq.get("solution_json", {})),
        teaching_json=json.dumps(sq.get("teaching_json", {})),
        status="complete",
    )
    db.add(q)
    return q


def seed_database(db: DBSession):
    """Seed demo questions into the database only when explicitly enabled.

    Default (production behaviour after 2026-07-09): do nothing so every new
    user starts with a completely empty question bank and builds their own
    knowledge asset. Set env ``MATHMIND_ENABLE_SEED=1`` to opt-in (used only
    for development / offline demos).
    """
    if os.getenv("MATHMIND_ENABLE_SEED", "").strip() not in ("1", "true", "yes"):
        logger.info("Seed disabled (MATHMIND_ENABLE_SEED not set); DB left untouched")
        return

    load_seed()
    for sq in _seed_questions:
        existing = db.query(Question).filter(Question.id == sq["id"]).first()
        if not existing:
            _add_question(db, sq)
    db.commit()
    logger.info("Database seeded with demo questions")