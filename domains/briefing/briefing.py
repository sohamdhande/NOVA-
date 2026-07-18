import json
import os
import logging
import urllib.request
import urllib.error
import sqlite3
from datetime import datetime, time, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

from tools.notion_tool import NotionTool
from core.priority_engine import PriorityEngine

# Configure logging
logger = logging.getLogger(__name__)

# Constants
BRIEFING_TIME = time(9, 0)  # 09:00 local time
STATE_FILE = os.path.join(os.path.dirname(__file__), "../data/briefing_state.json")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nova_logs.db")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

class BriefingEngine:
    """
    Manages the daily Morning Briefing.
    
    Responsibilities:
    - Check if briefing is due (09:00 or catch-up)
    - Fetch and score active tasks
    - Generate strict military-style report
    - Dispatch to Slack or Console
    - Persist last run state (SQLite)
    """
    
    def __init__(self):
        self.notion = NotionTool()
        self.priority_engine = PriorityEngine()
        
        # Initialize SQLite Connection
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False) # Thread-safe for API reads
        # Harden concurrency
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")
        
        self._create_table()
        self._migrate_from_json()

    def _create_table(self):
        """Create briefing_state table if it does not exist."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS briefing_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_run TEXT,
                updated_at TEXT
            )
        """)
        # Ensure default row exists
        cursor.execute("INSERT OR IGNORE INTO briefing_state (id, last_run, updated_at) VALUES (1, NULL, NULL)")
        self.conn.commit()

    def _migrate_from_json(self):
        """Migrate existing JSON state to SQLite if needed."""
        if os.path.exists(STATE_FILE):
            try:
                print("[Briefing] Migrating legacy JSON state to SQLite...")
                with open(STATE_FILE, "r") as f:
                    data = json.load(f)
                    last_run = data.get("last_run")
                
                if last_run:
                    cursor = self.conn.cursor()
                    # Only update if DB is null, don't overwrite newer DB state ideally, but here we assume migration is one-time
                    cursor.execute("""
                        UPDATE briefing_state 
                        SET last_run = ?, updated_at = ? 
                        WHERE id = 1 AND last_run IS NULL
                    """, (last_run, datetime.now().isoformat()))
                    self.conn.commit()
                
                # Rename JSON file to .bak to mark migration complete
                os.rename(STATE_FILE, STATE_FILE + ".bak")
                print("[Briefing] Migration complete. JSON file renamed to .bak")
                
            except Exception as e:
                logger.error(f"Migration failed: {e}")

    def get_last_run(self) -> Optional[str]:
        """Public accessor for last run date."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT last_run FROM briefing_state WHERE id = 1")
        row = cursor.fetchone()
        return row[0] if row else None

    def _save_state(self, last_run: str):
        """Save the last briefing date atomically to SQLite."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE briefing_state 
                SET last_run = ?, updated_at = ? 
                WHERE id = 1
            """, (last_run, datetime.now().isoformat()))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to save briefing state to DB: {e}")

    def _get_active_tasks(self) -> List[Dict[str, Any]]:
        """Fetch all active tasks from Notion."""
        # We need "all" active tasks to rank them properly, so we fetch a reasonably large limit
        # or iterate if pagination was supported (NotionTool simple implementation uses a limit)
        # For now, we'll request a higher limit to capture most tasks.
        response = self.notion.read_open_tasks(limit=100)
        
        if response.get("status") == "error":
            logger.error(f"Failed to fetch tasks for briefing: {response.get('message')}")
            return []
            
        return response.get("data", [])

    def _format_date(self, date_str: Optional[str]) -> str:
        """Format date string for display."""
        if not date_str:
            return "No deadline"
        try:
             # Try to parse and format
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return date_str

    def get_briefing_data(self) -> Dict[str, Any]:
        """
        Gather all data for the briefing and return as structured dict.
        Used by both generate_briefing (text) and API (JSON).
        """
        # 1. Fetch Data
        tasks = self._get_active_tasks()
        
        # 2. Score and Sort
        scored_tasks = self.priority_engine.process_tasks(tasks)
        
        # 3. Analyze Data
        now_aware = datetime.now().astimezone()
        today_date = now_aware.strftime('%Y-%m-%d')
        
        # Alerts Analysis
        overdue_tasks = []
        upcoming_deadlines = 0
        
        for task in scored_tasks:
            due_str = task.get("due_date")
            if due_str:
                try:
                    due_date = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
                    if due_date.tzinfo is None:
                        due_date = due_date.astimezone()
                    
                    if due_date < now_aware:
                        overdue_tasks.append(task)
                    elif due_date - now_aware <= timedelta(hours=48):
                        upcoming_deadlines += 1
                except ValueError:
                    pass

        # Priority Selection Logic
        total_active = len(scored_tasks)
        top_priorities = []
        
        if total_active <= 5:
            top_priorities = scored_tasks
        elif total_active <= 15:
            top_priorities = scored_tasks[:5]
        else:
            top_priorities = scored_tasks[:7]
            
        return {
            "date": today_date,
            "completed_yesterday": "TELEMETRY UNAVAILABLE", # Placeholder as per current logic
            "missed_yesterday": "TELEMETRY UNAVAILABLE",
            "overdue_tasks": overdue_tasks,
            "top_priorities": top_priorities,
            "alerts": {
                "upcoming_deadlines_48h": upcoming_deadlines,
                "total_active_tasks": total_active
            }
        }

    def generate_briefing(self) -> str:
        """Generate the briefing text."""
        data = self.get_briefing_data()
        
        # 4. Construct Output
        lines = []
        lines.append("MORNING BRIEFING")
        lines.append(f"Date: {data['date']}")
        lines.append("")
        
        lines.append("Performance Summary (Yesterday):")
        lines.append(f"Tasks completed: [{data['completed_yesterday']}]")
        lines.append(f"Tasks missed: [{data['missed_yesterday']}]")
        lines.append("Tasks rescheduled: [TELEMETRY UNAVAILABLE]")
        lines.append("")
        
        if data['overdue_tasks']:
            lines.append("OVERDUE TASKS")
            for t in data['overdue_tasks']:
                due_display = self._format_date(t.get("due_date"))
                lines.append(f"{t.get('title')} (due: {due_display})")
            lines.append("")
            
        lines.append("Priority Section:")
        if not data['top_priorities']:
            lines.append("No active tasks.")
            lines.append("Standby.")
        else:
            for t in data['top_priorities']:
                score = t.get("computed_score", 0)
                due_display = self._format_date(t.get("due_date"))
                lines.append(f"{t.get('title')}")
                lines.append(f"Score: {score}")
                lines.append(f"Due: {due_display}")
                lines.append("")
        
        lines.append("Alerts:")
        lines.append(f"Deadlines within 48h: {data['alerts']['upcoming_deadlines_48h']}")
        lines.append(f"Total active tasks: {data['alerts']['total_active_tasks']}")
        
        return "\n".join(lines)

    def send_briefing(self, content: str):
        """Dispatch the briefing."""
        if SLACK_WEBHOOK_URL:
            try:
                payload = json.dumps({"text": content}).encode('utf-8')
                req = urllib.request.Request(
                    SLACK_WEBHOOK_URL, 
                    data=payload, 
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req) as response:
                    if response.status == 200:
                        logger.info("Briefing sent to Slack.")
                    else:
                        logger.error(f"Failed to send to Slack: {response.status}")
            except urllib.error.URLError as e:
                logger.error(f"Error sending to Slack: {e}")
            except Exception as e:
                logger.error(f"Error sending to Slack: {e}")
        
        # Always log to console/logs as well
        print("\n" + "="*30)
        print(content)
        print("="*30 + "\n")

    def run_daily_check(self):
        """Check if briefing should run and execute if needed."""
        # Use timezone-aware time strictly
        now = datetime.now().astimezone()
        last_run_str = self.get_last_run()
        
        today_str = now.strftime("%Y-%m-%d")
        
        # Logic: 
        # 1. If already run today, skip.
        # 2. If not run today AND (time >= 09:00 OR missed), run.
        
        if last_run_str == today_str:
            return  # Already ran today
            
        # Check time constraint
        current_time = now.time()
        
        # BRIEFING_TIME is naive (09:00), need to compare carefully.
        # now.time() returns naive time but it's from an astimezone() datetime, 
        # so it represents the local time correctly.
        
        if current_time >= BRIEFING_TIME:
            logger.info("Initiating Morning Briefing...")
            try:
                content = self.generate_briefing()
                self.send_briefing(content)
                self._save_state(today_str)
                logger.info("Morning Briefing completed.")
            except Exception as e:
                logger.error(f"Failed to generate briefing: {e}")
