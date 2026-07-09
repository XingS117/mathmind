"""Wipe demo/seed learning data from a MathMind db.

After 2026-07-09 the product runs in single-user production mode. On the very
first launch we ship with 10 seed questions + demo sessions/mastery so the
grader/reviewer can see a populated UI. Once the site is officially open, run
this script once to reset every user (default guest + logged-in real users)
to an empty state:

  - delete every row in questions / sessions / mastery / review_schedule
  - keep users table (so u_default guest slot + u_admin stay)
  - keep user_settings (so LLM keys survive)
  - keep knowmap.json (still the 人教 B 版 7 册目录)

Usage:
    python scripts/reset_prod_data/wipe_demo_data.py
"""
from __future__ import annotations
import os, shutil, sqlite3, datetime, sys

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "mathmind.db")


def main() -> None:
    if not os.path.exists(DB):
        print(f"db not found: {DB}")
        sys.exit(1)

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{DB}.pre_wipe_{ts}.bak"
    shutil.copy2(DB, bak)
    print(f"backup -> {bak}")

    conn = sqlite3.connect(DB); cur = conn.cursor()
    try:
        counts_before = {}
        for t in ("questions", "sessions", "mastery", "review_schedule"):
            counts_before[t] = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print("before:", counts_before)

        cur.execute("DELETE FROM review_schedule")
        cur.execute("DELETE FROM mastery")
        cur.execute("DELETE FROM sessions")
        cur.execute("DELETE FROM questions")
        conn.commit()

        counts_after = {}
        for t in ("questions", "sessions", "mastery", "review_schedule"):
            counts_after[t] = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print("after:", counts_after)
        print("--- users kept ---")
        for row in cur.execute("SELECT id, username, role FROM users"):
            print(row)
        print("--- user_settings kept ---")
        n = cur.execute("SELECT COUNT(*) FROM user_settings").fetchone()[0]
        print("rows:", n)
    finally:
        conn.close()


if __name__ == "__main__":
    main()