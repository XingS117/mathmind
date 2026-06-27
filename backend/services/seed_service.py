import json, os, logging, random
from sqlalchemy.orm import Session as DBSession
from backend.models.question import Question
from backend.models.session import Session
from backend.models.mastery import Mastery

logger = logging.getLogger(__name__)
_seed_questions = []

def load_seed():
    global _seed_questions
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "seed_questions.json")
    if not os.path.exists(p):
        logger.warning(f"Seed file not found: {p}")
        return
    with open(p, encoding="utf-8") as f:
        _seed_questions = json.load(f)
    logger.info(f"Loaded {len(_seed_questions)} seed questions")

def get_random_seed() -> dict:
    if not _seed_questions:
        load_seed()
    return random.choice(_seed_questions) if _seed_questions else {}

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
        status="complete"
    )
    db.add(q)
    return q

def seed_database(db: DBSession):
    load_seed()
    uid = "u_default"

    # Questions
    for sq in _seed_questions:
        existing = db.query(Question).filter(Question.id == sq["id"]).first()
        if not existing:
            _add_question(db, sq)

    # Only create demo data if no sessions exist
    if db.query(Session).filter(Session.user_id == uid).count() == 0:
        logger.info("Creating demo learning sessions...")
        # Use first 4 seed question IDs for demo
        demo_qids = [sq["id"] for sq in _seed_questions[:4]]

        for i, qid in enumerate(demo_qids):
            steps_done = random.randint(2, 4)
            total = 4
            is_complete = random.choice([True, False])
            hints = random.randint(0, 2)
            s = Session(
                id=f"s_demo_{i}",
                user_id=uid, question_id=qid,
                status="completed" if is_complete else "in_progress",
                current_step=steps_done if not is_complete else total,
                total_steps=total, hints_used=hints,
                messages_json=json.dumps([]), steps_json=json.dumps([]),
                mastery_achieved=is_complete,
                mistakes_json=json.dumps([])
            )
            db.add(s)

        # Demo mastery records
        demo_nodes = ["一次函数", "函数求值", "配方法", "等差数列", "导数", "三角函数"]
        for i, node in enumerate(demo_nodes):
            score = random.uniform(0.3, 0.9)
            db.add(Mastery(
                id=f"m_demo_{i}", user_id=uid, node_id=node,
                score=round(score, 2),
                total_sessions=random.randint(1, 5),
                correct_sessions=random.randint(1, 4),
                last_reviewed=None
            ))

    db.commit()
    logger.info("Database seeded")