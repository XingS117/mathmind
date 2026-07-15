import json
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mathmind.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import backend.models.user
    import backend.models.referral
    import backend.models.operations
    import backend.models.question
    import backend.models.session
    import backend.models.mastery
    import backend.models.mastery_change_event
    import backend.models.settings
    import backend.models.review
    Base.metadata.create_all(bind=engine)
    _ensure_user_columns()
    _ensure_question_columns()
    _ensure_session_columns()
    _ensure_review_columns()
    _ensure_mastery_indexes()

def _ensure_question_columns():
    columns = {
        "raw_ocr_text": "TEXT DEFAULT ''",
        "analysis_source": "VARCHAR DEFAULT 'manual'",
        "analysis_confidence": "INTEGER DEFAULT 0",
        "review_status": "VARCHAR DEFAULT 'complete'",
        "needs_human_review": "BOOLEAN DEFAULT 0",
    }
    with engine.begin() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(questions)"))}
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE questions ADD COLUMN {name} {ddl}"))

def _ensure_user_columns():
    columns = {
        "is_active": "BOOLEAN NOT NULL DEFAULT 1",
        "updated_at": "DATETIME",
    }
    with engine.begin() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(users)"))}
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))

def _ensure_session_columns():
    columns = {
        "diagnostic_json": "TEXT DEFAULT '{}'",
        "mastery_applied_at": "DATETIME",
    }
    with engine.begin() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(sessions)"))}
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE sessions ADD COLUMN {name} {ddl}"))

def _ensure_review_columns():
    columns = {
        "mastery_applied_at": "DATETIME",
    }
    with engine.begin() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(review_schedule)"))}
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE review_schedule ADD COLUMN {name} {ddl}"))

def _ensure_mastery_indexes():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT id, user_id, node_id, score, total_sessions, correct_sessions,
                   variant_passed, last_reviewed, manual_adjustments
            FROM mastery
            ORDER BY user_id, node_id, id
        """)).mappings().all()
        groups = {}
        for row in rows:
            groups.setdefault((row["user_id"], row["node_id"]), []).append(row)
        for duplicates in groups.values():
            if len(duplicates) < 2:
                continue
            canonical, *extras = duplicates
            latest_reviewed = max(
                (row["last_reviewed"] for row in duplicates if row["last_reviewed"] is not None),
                key=str,
                default=None,
            )
            manual_adjustments = []
            for row in duplicates:
                value = row["manual_adjustments"]
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        value = []
                if isinstance(value, list):
                    manual_adjustments.extend(value)
            conn.execute(text("""
                UPDATE mastery
                SET score = :score,
                    total_sessions = :total_sessions,
                    correct_sessions = :correct_sessions,
                    variant_passed = :variant_passed,
                    last_reviewed = :last_reviewed,
                    manual_adjustments = :manual_adjustments
                WHERE id = :id
            """), {
                "id": canonical["id"],
                "score": min(1.0, max(float(row["score"] or 0.0) for row in duplicates)),
                "total_sessions": sum(int(row["total_sessions"] or 0) for row in duplicates),
                "correct_sessions": sum(int(row["correct_sessions"] or 0) for row in duplicates),
                "variant_passed": any(bool(row["variant_passed"]) for row in duplicates),
                "last_reviewed": latest_reviewed,
                "manual_adjustments": json.dumps(manual_adjustments, ensure_ascii=False),
            })
            for duplicate in extras:
                conn.execute(text("DELETE FROM mastery WHERE id = :id"), {"id": duplicate["id"]})
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_mastery_user_node ON mastery (user_id, node_id)"
        ))
