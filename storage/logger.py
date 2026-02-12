import sqlite3
import os
from datetime import datetime

# Database file path (stored in project root)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nova_logs.db")


class ExecutionLogger:
    """Logs all NOVA executions to a local SQLite database."""

    def __init__(self):
        """Initialize database connection and create table if needed."""
        self.conn = sqlite3.connect(DB_PATH)
        self._create_table()

    def _create_table(self):
        """Create executions table if it does not exist."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_command TEXT,
                intent TEXT,
                domain TEXT,
                action TEXT,
                risk TEXT,
                status TEXT,
                response_summary TEXT
            )
        """)
        self.conn.commit()

    def log_execution(self, user_command, parsed_plan, final_response, status):
        """Record a single execution to the database.

        Args:
            user_command: Original user input string.
            parsed_plan: Structured plan dict from controller.
            final_response: The response string shown to user.
            status: 'success', 'error', or 'planned'.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Truncate response for storage (keep first 500 chars)
        summary = final_response[:500] if final_response else ""

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO executions
            (timestamp, user_command, intent, domain, action, risk, status, response_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            user_command,
            parsed_plan.get("intent", "unknown"),
            parsed_plan.get("domain", "unknown"),
            parsed_plan.get("action", "none"),
            parsed_plan.get("risk", "unknown"),
            status,
            summary
        ))
        self.conn.commit()

    def get_recent_logs(self, limit=5):
        """Retrieve the most recent execution records.

        Returns:
            List of tuples (id, timestamp, user_command, intent, domain,
                           action, risk, status, response_summary).
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, user_command, intent, domain,
                   action, risk, status, response_summary
            FROM executions
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()

    def close(self):
        """Close database connection."""
        self.conn.close()
