import sqlite3

DB_PATH = "checkpoints.db"


def init_rules_store():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rules (
                action_type TEXT PRIMARY KEY,
                auto_approve INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def is_auto_approved(action_type: str) -> bool:
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    try:
        cursor = conn.execute(
            "SELECT auto_approve FROM rules WHERE action_type = ?",
            (action_type,),
        )
        row = cursor.fetchone()
    finally:
        conn.close()
    return bool(row and row[0])


def set_auto_approve(action_type: str, enabled: bool) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    try:
        conn.execute(
            """
            INSERT INTO rules (action_type, auto_approve) VALUES (?, ?)
            ON CONFLICT(action_type) DO UPDATE SET auto_approve = excluded.auto_approve
            """,
            (action_type, int(enabled)),
        )
        conn.commit()
    finally:
        conn.close()


def has_rule(action_type: str) -> bool:
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    try:
        cursor = conn.execute(
            "SELECT 1 FROM rules WHERE action_type = ?",
            (action_type,),
        )
        row = cursor.fetchone()
    finally:
        conn.close()
    return row is not None