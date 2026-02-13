
import sqlite3
import os
import json
from datetime import datetime, timedelta

# Database path (reuse existing log db)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nova_logs.db")

class TelemetryLogger:
    def __init__(self):
        """Initialize connection to telemetry table."""
        try:
            self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._create_table()
        except Exception as e:
            print(f"Telemetry Init Error: {e}")
            self.conn = None

    def _create_table(self):
        if not self.conn: return
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                metric_type TEXT,
                metric_value INTEGER,
                metadata TEXT
            )
        """)
        self.conn.commit()

    ALLOWED_METRICS = {
        "planner_invoked", 
        "planner_failed", 
        "validation_failed", 
        "correction_invoked", 
        "correction_failed", 
        "mutation_attempt", 
        "mutation_success", 
        "mutation_blocked", 
        "file_ingested", 
        "memory_stored", 
        "daemon_heartbeat"
    }

    def increment(self, metric_type, value=1, metadata=None):
        """Log a metric event safely with strict whitelist enforcement.
        
        Args:
            metric_type: Metric name (must be in ALLOWED_METRICS).
            value: Increment amount (default 1).
            metadata: Optional metadata dict.
        """
        if not self.conn: 
            return

        # STRICT WHITELIST - silently ignore unauthorized metrics
        if metric_type not in self.ALLOWED_METRICS:
            # Only warn in debug mode
            import config
            if config.DEBUG:
                print(f"[Telemetry] Denied metric '{metric_type}'")
            return
        
        try:
            timestamp = datetime.now().isoformat()
            meta_json = json.dumps(metadata) if metadata else None
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO telemetry_metrics (timestamp, metric_type, metric_value, metadata)
                VALUES (?, ?, ?, ?)
            """, (timestamp, metric_type, value, meta_json))
            self.conn.commit()
        except Exception as e:
            # Telemetry should never crash the app
            import config
            if config.DEBUG:
                print(f"Telemetry Write Error: {e}")

    def get_summary(self, days=1):
        """Get aggregated metrics for the last N days."""
        if not self.conn: return {}
        
        try:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT metric_type, SUM(metric_value)
                FROM telemetry_metrics
                WHERE timestamp >= ?
                GROUP BY metric_type
            """, (cutoff,))
            
            return dict(cursor.fetchall())
        except Exception as e:
            print(f"Telemetry Read Error: {e}")
            return {}

    def close(self):
        if self.conn:
            self.conn.close()
