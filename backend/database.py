"""
SQLite database. Two tables:
  - users: one row per registered account
  - meetings: one row per processed meeting, scoped to a user_id
"""
import sqlite3
import json
import uuid
from datetime import datetime, timezone
from config import DATABASE_PATH


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            filename TEXT,
            status TEXT DEFAULT 'uploaded',
            meeting_type TEXT DEFAULT 'General',
            language TEXT DEFAULT 'auto',
            transcript TEXT,
            summary TEXT,
            sentiment TEXT,
            action_items TEXT,
            email_subject TEXT,
            email_body TEXT,
            created_at TEXT
        )
    """)

    for column, col_type in [
        ("meeting_type", "TEXT DEFAULT 'General'"),
        ("sentiment", "TEXT"),
        ("user_id", "TEXT"),
        ("language", "TEXT DEFAULT 'auto'"),
    ]:
        try:
            conn.execute(f"ALTER TABLE meetings ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()


# ---------------- Users ----------------

def create_user(email: str, password_hash: str) -> str:
    user_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (user_id, email.lower().strip(), password_hash, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------- Meetings ----------------

def create_meeting(meeting_id: str, filename: str, user_id: str, meeting_type: str = "General", language: str = "auto"):
    conn = get_connection()
    conn.execute(
        """INSERT INTO meetings (id, user_id, filename, status, meeting_type, language, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (meeting_id, user_id, filename, "uploaded", meeting_type, language, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def update_meeting(meeting_id: str, **fields):
    conn = get_connection()
    columns = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [meeting_id]
    conn.execute(f"UPDATE meetings SET {columns} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_meeting(meeting_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    result = dict(row)
    if result.get("action_items"):
        result["action_items"] = json.loads(result["action_items"])
    return result


def list_meetings(user_id: str):
    """Only returns meetings belonging to the given user."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, filename, status, meeting_type, language, created_at
           FROM meetings WHERE user_id = ? ORDER BY created_at DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_meetings_with_content(user_id: str):
    """
    Phase 4: like list_meetings, but includes transcript/summary too —
    used by the cross-meeting search feature, which needs the actual
    content to score relevance against, not just metadata.
    """
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, filename, status, meeting_type, language, created_at, summary, transcript
           FROM meetings WHERE user_id = ? AND status = 'done' ORDER BY created_at DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_analytics(user_id: str) -> dict:
    """
    Phase 4: aggregate stats for the Analytics dashboard. Kept as plain
    SQL queries rather than pulling everything into Python and
    aggregating there — lets SQLite do the counting, which stays fast
    even as meeting history grows.
    """
    conn = get_connection()

    total_meetings = conn.execute(
        "SELECT COUNT(*) as c FROM meetings WHERE user_id = ?", (user_id,)
    ).fetchone()["c"]

    by_type = conn.execute(
        """SELECT meeting_type, COUNT(*) as c FROM meetings
           WHERE user_id = ? AND status = 'done' GROUP BY meeting_type""",
        (user_id,),
    ).fetchall()

    by_status = conn.execute(
        "SELECT status, COUNT(*) as c FROM meetings WHERE user_id = ? GROUP BY status",
        (user_id,),
    ).fetchall()

    per_week = conn.execute(
        """SELECT strftime('%Y-%W', created_at) as week, COUNT(*) as c
           FROM meetings WHERE user_id = ?
           GROUP BY week ORDER BY week DESC LIMIT 8""",
        (user_id,),
    ).fetchall()

    action_item_rows = conn.execute(
        "SELECT action_items FROM meetings WHERE user_id = ? AND action_items IS NOT NULL",
        (user_id,),
    ).fetchall()

    conn.close()

    total_action_items = 0
    completed_action_items = 0
    for row in action_item_rows:
        try:
            items = json.loads(row["action_items"])
            total_action_items += len(items)
            completed_action_items += sum(1 for i in items if i.get("done"))
        except (json.JSONDecodeError, TypeError):
            continue

    return {
        "total_meetings": total_meetings,
        "by_type": {r["meeting_type"] or "General": r["c"] for r in by_type},
        "by_status": {r["status"]: r["c"] for r in by_status},
        "per_week": [{"week": r["week"], "count": r["c"]} for r in reversed(per_week)],
        "total_action_items": total_action_items,
        "completed_action_items": completed_action_items,
    }