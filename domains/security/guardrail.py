
import sqlite3
import os
from datetime import datetime

# Database path (reuse existing log db)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nova_logs.db")

# Limits
LIMITS = {
    "create_event": 5,        # Max daily calendar creations
    "update_event": 5,        # Max daily calendar updates
    "delete_event": 2,        # Max daily calendar deletions
    "create_task": 10,        # Max daily task creations
    "update_task": 10,        # Max daily task updates
    "update_task_status": 10  # Alias for update_task
}

class MutationGuardrail:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        # Harden concurrency
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")
        print(f"[SQLite] WAL mode enabled for MutationGuardrail")
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_mutations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                domain TEXT,
                action TEXT,
                timestamp TEXT
            )
        """)
        self.conn.commit()

    def check_constraints(self, domain, action):
        """
        Check if an action violates daily limits.
        
        Returns:
            (bool, reason): True if allowed, False if blocked.
        """
        # Read-only actions always allowed
        if "read" in action or "search" in action or "get" in action:
            return True, None

        limit = LIMITS.get(action)
        if limit is None:
            # If action not strictly limited, allow it (e.g. specialized tools)
            # Default to safe unless it matches mutation patterns
            if "create" in action or "update" in action or "delete" in action or "store" in action:
                 # Implicit limit for unknown mutations
                 limit = 10 
            else:
                 return True, None

        
        # --- TELEMETRY ---
        from core.telemetry import TelemetryLogger
        telemetry = TelemetryLogger()
        if "read" not in action and "search" not in action and "get" not in action:
             telemetry.increment("mutation_attempt", metadata={"domain": domain, "action": action})
        # -----------------

        today = datetime.now().strftime("%Y-%m-%d")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM daily_mutations 
            WHERE date = ? AND action = ?
        """, (today, action))
        
        count = cursor.fetchone()[0]
        
        if count >= limit:
            telemetry.increment("mutation_blocked", metadata={"reason": "limit_exceeded", "action": action})
            return False, f"Daily limit exceeded for '{action}' ({count}/{limit})."
            
        return True, None

    def record_mutation(self, domain, action):
        """Log a successful mutation to increment the counter."""
        if "read" in action or "search" in action:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO daily_mutations (date, domain, action, timestamp)
            VALUES (?, ?, ?, ?)
        """, (today, domain, action, timestamp))
        self.conn.commit()

    def close(self):
        self.conn.close()
