import sqlite3
from datetime import datetime, timezone

from database import database_path


def init_decision_log():
    conn = sqlite3.connect(database_path(), timeout=10.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                approved INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def log_decision(action_type: str, approved: bool) -> None:
    conn = sqlite3.connect(database_path(), timeout=10.0)
    try:
        conn.execute(
            "INSERT INTO decisions (action_type, approved, created_at) VALUES (?, ?, ?)",
            (action_type, int(approved), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def count_consecutive_approvals(action_type: str) -> int:
    conn = sqlite3.connect(database_path(), timeout=10.0)
    try:
        cursor = conn.execute(
            "SELECT approved FROM decisions WHERE action_type = ? ORDER BY id DESC",
            (action_type,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    count = 0
    for (approved,) in rows:
        if approved:
            count += 1
        else:
            break
    return count