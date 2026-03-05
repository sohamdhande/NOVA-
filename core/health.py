import sqlite3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

# Constants
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nova_logs.db")
logger = logging.getLogger(__name__)


class HealthEngine:
    """
    Advanced Dynamic System Health Engine for NOVA.
    Computes raw health from task/expense/daemon metrics,
    applies exponential smoothing, classifies zones,
    and detects trigger conditions with cooldown.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")
        self._create_table()

    # ------------------------------------------------------------------ #
    #  Table Management                                                    #
    # ------------------------------------------------------------------ #

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                previous_health REAL NOT NULL,
                last_updated TEXT,
                last_trigger TEXT
            )
        """)
        # Initialize singleton row if missing
        cursor.execute("SELECT id FROM system_state WHERE id = 1")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO system_state (id, previous_health, last_updated, last_trigger)
                VALUES (1, 100.0, ?, NULL)
            """, (datetime.now().isoformat(),))
        self.conn.commit()

    def _get_state(self) -> Tuple[float, Optional[str], Optional[str]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT previous_health, last_updated, last_trigger FROM system_state WHERE id = 1"
        )
        return cursor.fetchone()

    def _update_state(self, new_health: float, trigger_timestamp: Optional[str] = None):
        cursor = self.conn.cursor()
        now_iso = datetime.now().isoformat()
        if trigger_timestamp:
            cursor.execute("""
                UPDATE system_state
                SET previous_health = ?, last_updated = ?, last_trigger = ?
                WHERE id = 1
            """, (new_health, now_iso, trigger_timestamp))
        else:
            cursor.execute("""
                UPDATE system_state
                SET previous_health = ?, last_updated = ?
                WHERE id = 1
            """, (new_health, now_iso))
        self.conn.commit()

    # ------------------------------------------------------------------ #
    #  Raw Health Calculation                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _compute_raw_health(metrics: Dict) -> float:
        """
        Compute raw health score from metrics.

        Expected keys:
            overdue_count         int
            deadlines_48h         int
            deadlines_24h         int
            active_tasks          int
            expense_logged_today  bool
            missed_days_this_month int
            last_7_day_streak     bool
            daemon_crash_recent   bool
            daemon_uptime_hours   float
        """
        health = 100.0

        # --- Academic (capped at -40) ---
        academic_penalty = 0.0
        academic_penalty += metrics.get("overdue_count", 0) * 8
        academic_penalty += metrics.get("deadlines_48h", 0) * 4
        if metrics.get("active_tasks", 0) > 12:
            academic_penalty += 5
        academic_penalty = min(academic_penalty, 40)
        health -= academic_penalty

        # --- Time Pressure ---
        if metrics.get("deadlines_24h", 0) >= 3:
            health -= 8
        # Bonus: no deadlines within 72h (approximated as deadlines_48h == 0)
        if metrics.get("deadlines_48h", 0) == 0 and metrics.get("deadlines_24h", 0) == 0:
            health += 3

        # --- Discipline ---
        if not metrics.get("expense_logged_today", True):
            health -= 6
        if metrics.get("missed_days_this_month", 0) > 3:
            health -= 8
        if metrics.get("last_7_day_streak", False):
            health += 4

        # --- System ---
        if metrics.get("daemon_crash_recent", False):
            health -= 10
        if metrics.get("daemon_uptime_hours", 0) > 48:
            health += 3

        # Clamp
        return max(20.0, min(100.0, health))

    # ------------------------------------------------------------------ #
    #  Zone Classification                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _determine_zone(health: int) -> str:
        if health >= 90:
            return "stable"
        elif health >= 75:
            return "controlled"
        elif health >= 60:
            return "elevated"
        else:
            return "critical"

    # ------------------------------------------------------------------ #
    #  Trigger Detection                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _should_trigger(
        smoothed: int,
        prev_health: float,
        last_trigger: Optional[str],
    ) -> bool:
        """
        Trigger if (outside cooldown):
          - health drop >= 8
          - crossed boundary: >=75 → <75  OR  >=60 → <60
          - health < 55
        Cooldown: 30 minutes since last_trigger.
        """
        # Cooldown check
        if last_trigger:
            try:
                last_dt = datetime.fromisoformat(last_trigger)
                if (datetime.now() - last_dt) < timedelta(minutes=30):
                    return False
            except (ValueError, TypeError):
                pass  # Corrupt timestamp — ignore cooldown

        drop = prev_health - smoothed

        # Threshold crossing
        crossed = (
            (prev_health >= 75 and smoothed < 75)
            or (prev_health >= 60 and smoothed < 60)
        )

        return drop >= 8 or crossed or smoothed < 55

    # ------------------------------------------------------------------ #
    #  Main Entry Point                                                    #
    # ------------------------------------------------------------------ #

    def calculate_health(self, metrics: Dict) -> Dict:
        """
        Full pipeline: raw → smooth → zone → trigger → persist.

        Returns:
            {
                "system_health": int,
                "health_zone": str,
                "health_trigger": bool
            }
        """
        # 1. Raw
        raw = self._compute_raw_health(metrics)

        # 2. Smoothing
        prev_health, _last_updated, last_trigger = self._get_state()
        smoothed = round((prev_health * 0.75) + (raw * 0.25))

        # 3. Zone
        zone = self._determine_zone(smoothed)

        # 4. Trigger
        triggered = self._should_trigger(smoothed, prev_health, last_trigger)

        # 5. Persist
        trigger_ts = datetime.now().isoformat() if triggered else None
        self._update_state(float(smoothed), trigger_ts)

        return {
            "system_health": smoothed,
            "health_zone": zone,
            "health_trigger": triggered,
        }
