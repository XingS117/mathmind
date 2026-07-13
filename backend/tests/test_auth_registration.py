import hashlib
import os
import tempfile
import unittest

from sqlalchemy import create_engine, text

import backend.database as database
from backend.services.auth_service import hash_password, needs_password_upgrade, verify_password


def legacy_hash(password: str) -> str:
    salt = "legacy-salt"
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${digest}"


class PasswordMigrationTest(unittest.TestCase):
    def test_new_password_hash_uses_scrypt_and_verifies(self):
        encoded = hash_password("pw-123456")

        self.assertTrue(encoded.startswith("scrypt$"))
        self.assertTrue(verify_password("pw-123456", encoded))
        self.assertFalse(needs_password_upgrade(encoded))

    def test_legacy_password_is_accepted_then_marked_for_upgrade(self):
        encoded = legacy_hash("pw-123456")

        self.assertTrue(verify_password("pw-123456", encoded))
        self.assertTrue(needs_password_upgrade(encoded))


class DatabaseMigrationTest(unittest.TestCase):
    def test_init_db_adds_is_active_to_legacy_users_table(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
            db_path = handle.name
        temp_engine = create_engine(f"sqlite:///{db_path}")
        original_engine = database.engine
        try:
            with temp_engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE users (
                        id VARCHAR PRIMARY KEY,
                        username VARCHAR NOT NULL UNIQUE,
                        password_hash VARCHAR,
                        name VARCHAR NOT NULL,
                        role VARCHAR,
                        school_level VARCHAR,
                        created_at DATETIME
                    )
                """))

            database.engine = temp_engine
            database.init_db()
            database.init_db()

            with temp_engine.connect() as conn:
                columns = {row[1] for row in conn.execute(text("PRAGMA table_info(users)"))}
            self.assertIn("is_active", columns)
            self.assertIn("updated_at", columns)
        finally:
            database.engine = original_engine
            temp_engine.dispose()
            os.unlink(db_path)


if __name__ == "__main__":
    unittest.main()
