import sqlite3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nova_logs.db")
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Advisory Templates (deterministic, zone-aware)                      #
# ------------------------------------------------------------------ #

_TONE = {
    "stable": "calm",
    "controlled": "directive",
    "elevated": "tactical",
    "critical": "urgent",
}

_TEMPLATES = {
    "morning": {
        "stable": {
            "message": "Daily operational window active, BOSS. Primary focus: Complete highest priority task.",
            "recommendations": [
                "Review today's priority queue.",
                "Confirm deadlines for the next 48 hours.",
            ],
        },
        "controlled": {
            "message": "Morning check-in. Controlled state — attention required on pending items.",
            "recommendations": [
                "Address top overdue task first.",
                "Verify expense log is current.",
            ],
        },
        "elevated": {
            "message": "Morning brief. Elevated state — multiple areas need attention.",
            "recommendations": [
                "Clear overdue backlog immediately.",
                "Log any missing expense entries.",
                "Review upcoming deadlines.",
            ],
        },
        "critical": {
            "message": "Morning brief. Critical state — immediate corrective action required.",
            "recommendations": [
                "Resolve all overdue tasks before new work.",
                "Audit missed expense days.",
                "Confirm daemon operational status.",
            ],
        },
    },
    "deadline": {
        "stable": {
            "message": "Multiple deadlines within 24 hours. Recommend dedicated completion window.",
            "recommendations": [
                "Block focused time for deadline tasks.",
                "Defer non-urgent items.",
            ],
        },
        "controlled": {
            "message": "Deadline pressure detected. 2+ tasks due within 24 hours.",
            "recommendations": [
                "Prioritize deadline tasks immediately.",
                "Reduce context switching.",
            ],
        },
        "elevated": {
            "message": "High deadline density. Immediate scheduling required.",
            "recommendations": [
                "Begin closest deadline task now.",
                "Postpone all non-deadline work.",
            ],
        },
        "critical": {
            "message": "Critical deadline convergence. Multiple tasks at risk of overdue.",
            "recommendations": [
                "Execute deadline tasks in priority order.",
                "Notify stakeholders if completion at risk.",
            ],
        },
    },
    "discipline": {
        "stable": {
            "message": "Expense entry pending. Log before 2200 hours.",
            "recommendations": ["Log today's expenses."],
        },
        "controlled": {
            "message": "Expense entry pending. Logging consistency at risk.",
            "recommendations": [
                "Log today's expenses now.",
                "Review recent missing days.",
            ],
        },
        "elevated": {
            "message": "Expense discipline gap. Log immediately.",
            "recommendations": [
                "Log today's expenses.",
                "Audit this week's entries.",
            ],
        },
        "critical": {
            "message": "Expense tracking failure. Immediate entry required.",
            "recommendations": [
                "Log today's expenses now.",
                "Backfill any missing days.",
            ],
        },
    },
    "idle": {
        "stable": {
            "message": "Overdue tasks remain unresolved. No recent activity detected.",
            "recommendations": ["Resume work on overdue items."],
        },
        "controlled": {
            "message": "Overdue tasks unresolved with no recent activity. Attention required.",
            "recommendations": [
                "Begin work on highest priority overdue task.",
                "Log activity to confirm engagement.",
            ],
        },
        "elevated": {
            "message": "Overdue backlog growing. No activity in the last 4 hours.",
            "recommendations": [
                "Immediately start overdue task.",
                "Reduce idle time.",
            ],
        },
        "critical": {
            "message": "Critical idle state. Overdue tasks accumulating with zero activity.",
            "recommendations": [
                "Begin overdue work immediately.",
                "Consider timeline renegotiation if blocked.",
            ],
        },
    },
    "risk": {
        "stable": {
            "message": "Health trigger activated. Review system status.",
            "recommendations": ["Check summary for anomalies."],
        },
        "controlled": {
            "message": "Health drop detected. Controlled degradation in progress.",
            "recommendations": [
                "Identify primary penalty source.",
                "Take corrective action.",
            ],
        },
        "elevated": {
            "message": "Significant health decline. Multiple subsystems affected.",
            "recommendations": [
                "Address top penalty category.",
                "Stabilize before taking new work.",
            ],
        },
        "critical": {
            "message": "System health critical. Immediate intervention required.",
            "recommendations": [
                "Stop all new work.",
                "Resolve overdue tasks.",
                "Restore daemon if offline.",
                "Log missing expenses.",
            ],
        },
    },
}


def _severity_for_zone(zone: str) -> str:
    if zone == "stable":
        return "info"
    elif zone == "controlled":
        return "info"
    elif zone == "elevated":
        return "warning"
    else:
        return "critical"


# ------------------------------------------------------------------ #
#  ContextEngine                                                       #
# ------------------------------------------------------------------ #


class ContextEngine:
    """
    Aggregates situational state, decides proactive trigger,
    generates deterministic advisory payload.
    """

    MAX_DAILY = 3
    MIN_GAP_HOURS = 2

    def __init__(self, db_path=None, notion_tool=None, expense_manager=None,
                 daemon=None, health_engine=None):
        self.db_path = db_path or DB_PATH
        self.notion_tool = notion_tool
        self.expense_manager = expense_manager
        self.daemon = daemon
        self.health_engine = health_engine

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")
        self._create_table()

    # ------------------------------------------------------------ #
    #  Proactive State Table                                         #
    # ------------------------------------------------------------ #

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proactive_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_proactive TEXT,
                daily_count INTEGER NOT NULL DEFAULT 0,
                last_reset_date TEXT
            )
        """)
        cursor.execute("SELECT id FROM proactive_state WHERE id = 1")
        if not cursor.fetchone():
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
                INSERT INTO proactive_state (id, last_proactive, daily_count, last_reset_date)
                VALUES (1, NULL, 0, ?)
            """, (today,))
        self.conn.commit()

    def _get_proactive_state(self):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT last_proactive, daily_count, last_reset_date FROM proactive_state WHERE id = 1"
        )
        return cursor.fetchone()

    def _record_proactive(self, now: datetime = None):
        now = now or datetime.now()
        today = now.strftime("%Y-%m-%d")
        last_proactive, daily_count, last_reset_date = self._get_proactive_state()

        # Reset if new day
        if last_reset_date != today:
            daily_count = 0
            last_reset_date = today

        daily_count += 1
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE proactive_state
            SET last_proactive = ?, daily_count = ?, last_reset_date = ?
            WHERE id = 1
        """, (now.isoformat(), daily_count, last_reset_date))
        self.conn.commit()

    # ------------------------------------------------------------ #
    #  Context Snapshot                                               #
    # ------------------------------------------------------------ #

    def get_context_snapshot(self, health_result: Dict = None,
                            overdue_count: int = 0,
                            deadlines_24h: int = 0,
                            deadlines_48h: int = 0,
                            active_tasks: int = 0,
                            expense_logged_today: bool = True,
                            missed_days_month: int = 0,
                            daemon_uptime_hours: float = 0.0,
                            now: datetime = None) -> Dict:
        """Build context snapshot from pre-computed values."""
        now = now or datetime.now()
        health = health_result.get("system_health", 100) if health_result else 100
        zone = health_result.get("health_zone", "stable") if health_result else "stable"
        health_trigger = health_result.get("health_trigger", False) if health_result else False

        return {
            "health": health,
            "zone": zone,
            "health_trigger": health_trigger,
            "overdue_count": overdue_count,
            "deadlines_24h": deadlines_24h,
            "deadlines_48h": deadlines_48h,
            "active_tasks": active_tasks,
            "expense_logged_today": expense_logged_today,
            "missed_days_month": missed_days_month,
            "daemon_uptime_hours": daemon_uptime_hours,
            "hour_of_day": now.hour,
            "recent_activity_flag": self._check_recent_activity(now),
        }

    def _check_recent_activity(self, now: datetime = None) -> bool:
        """True if mutation_success logged in the last 4 hours."""
        now = now or datetime.now()
        cutoff = (now - timedelta(hours=4)).isoformat()
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM telemetry_metrics
                WHERE metric_type = 'mutation_success' AND timestamp >= ?
            """, (cutoff,))
            row = cursor.fetchone()
            return row[0] > 0 if row else False
        except Exception:
            # Table might not exist in test DBs
            return False

    # ------------------------------------------------------------ #
    #  Proactive Trigger Logic                                       #
    # ------------------------------------------------------------ #

    def should_trigger_proactive(self, snapshot: Dict, now: datetime = None) -> Optional[str]:
        """
        Evaluate 5 trigger conditions (A–E).
        Returns trigger type string or None.
        Enforces daily max + 2-hour gap.
        """
        now = now or datetime.now()

        # --- Strict limits ---
        last_proactive, daily_count, last_reset_date = self._get_proactive_state()
        today = now.strftime("%Y-%m-%d")

        # Reset daily count if new day
        if last_reset_date != today:
            daily_count = 0

        if daily_count >= self.MAX_DAILY:
            return None

        # 2-hour gap
        if last_proactive:
            try:
                last_dt = datetime.fromisoformat(last_proactive)
                if (now - last_dt) < timedelta(hours=self.MIN_GAP_HOURS):
                    return None
            except (ValueError, TypeError):
                pass

        hour = snapshot.get("hour_of_day", now.hour)

        # A) Health Trigger
        if snapshot.get("health_trigger", False):
            return "risk"

        # B) Morning Window
        if 8 <= hour <= 10:
            # Check no proactive sent today
            if daily_count == 0 or last_reset_date != today:
                return "morning"

        # C) Discipline Risk
        if hour >= 21 and not snapshot.get("expense_logged_today", True):
            return "discipline"

        # D) Deadline Pressure
        if snapshot.get("deadlines_24h", 0) >= 2:
            return "deadline"

        # E) Idle Risk
        if (snapshot.get("overdue_count", 0) > 0
                and not snapshot.get("recent_activity_flag", True)):
            # Additional check: no proactive in last 2 hours (already enforced by gap above)
            return "idle"

        return None

    # ------------------------------------------------------------ #
    #  Advisory Generation                                            #
    # ------------------------------------------------------------ #

    def generate_advisory(self, snapshot: Dict, trigger_type: str) -> Dict:
        """
        Generate deterministic advisory payload.
        Returns { type, severity, message, recommendations }
        """
        zone = snapshot.get("zone", "stable")
        severity = _severity_for_zone(zone)

        templates = _TEMPLATES.get(trigger_type, _TEMPLATES["risk"])
        template = templates.get(zone, templates["stable"])

        return {
            "type": trigger_type,
            "severity": severity,
            "message": template["message"],
            "recommendations": list(template["recommendations"]),
        }

    # ------------------------------------------------------------ #
    #  Main Entry Point                                               #
    # ------------------------------------------------------------ #

    def evaluate(self, snapshot: Dict, now: datetime = None) -> Dict:
        """
        Full pipeline: check trigger → generate advisory → persist.
        Returns { triggered: bool, payload: advisory | None }
        """
        now = now or datetime.now()
        trigger_type = self.should_trigger_proactive(snapshot, now=now)

        if trigger_type is None:
            return {"triggered": False, "payload": None}

        advisory = self.generate_advisory(snapshot, trigger_type)
        self._record_proactive(now=now)

        return {"triggered": True, "payload": advisory}
