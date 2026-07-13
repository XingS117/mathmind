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
    import backend.models.operations
    import backend.models.question
    import backend.models.session
    import backend.models.mastery
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
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_mastery_user_node ON mastery (user_id, node_id)"
        ))
