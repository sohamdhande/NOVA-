"""
NOVA Reminder Tool — Phase B
SQLite-backed reminders with natural-language time parsing via dateparser.
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional

import dateparser

# ── Database path ─────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nova_logs.db")


def _get_conn() -> sqlite3.Connection:
    """Return a connection with the reminders table guaranteed to exist."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def set_reminder(message: str, natural_time: str) -> dict:
    """
    Parse *natural_time* and create a pending reminder.

    Returns:
        {"status": "set", "message": ..., "at": ISO-datetime}
    """
    parsed_dt = dateparser.parse(
        natural_time,
        settings={
            "PREFER_DATES_FROM": "future",
            "TIMEZONE": "Asia/Kolkata",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )

    if parsed_dt is None:
        return {
            "status": "error",
            "message": message,
            "error": f"Could not understand time: '{natural_time}'",
        }

    remind_at_iso = parsed_dt.isoformat()

    conn = _get_conn()
    conn.execute(
        "INSERT INTO reminders (message, remind_at, status) VALUES (?, ?, 'pending')",
        (message, remind_at_iso),
    )
    conn.commit()
    conn.close()

    return {"status": "set", "message": message, "at": remind_at_iso}


def get_pending_reminders() -> list[dict]:
    """Return all reminders where status=pending and remind_at <= now."""
    now_iso = datetime.now().isoformat()
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, message, remind_at FROM reminders "
        "WHERE status = 'pending' AND remind_at <= ? "
        "ORDER BY remind_at ASC",
        (now_iso,),
    ).fetchall()
    conn.close()
    return [{"id": r[0], "message": r[1], "remind_at": r[2]} for r in rows]


def get_all_pending() -> list[dict]:
    """Return ALL pending reminders regardless of time (for listing)."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, message, remind_at FROM reminders "
        "WHERE status = 'pending' "
        "ORDER BY remind_at ASC",
    ).fetchall()
    conn.close()
    return [{"id": r[0], "message": r[1], "remind_at": r[2]} for r in rows]


def mark_done(reminder_id: int) -> None:
    """Mark a reminder as done."""
    conn = _get_conn()
    conn.execute(
        "UPDATE reminders SET status = 'done' WHERE id = ?",
        (reminder_id,),
    )
    conn.commit()
    conn.close()
