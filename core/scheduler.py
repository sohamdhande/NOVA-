import schedule
import threading
import time
import json
import sqlite3
import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class ScheduledTask:
    id: str
    name: str
    instruction: str
    schedule_type: str  # daily/weekly/hourly/once
    schedule_time: str  # "09:00" or "monday 09:00"
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0

class TaskScheduler:
    
    def __init__(self):
        self._tasks: dict = {}
        self._thread = None
        self._running = False
        self._db = "nova_logs.db"
        self._load_tasks()
    
    def _load_tasks(self):
        """Load saved tasks from DB."""
        try:
            conn = sqlite3.connect(
                self._db,
                check_same_thread=False
            )
            conn.execute("""
                CREATE TABLE IF NOT EXISTS 
                scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    instruction TEXT,
                    schedule_type TEXT,
                    schedule_time TEXT,
                    enabled INTEGER DEFAULT 1,
                    last_run TEXT,
                    run_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()
            rows = conn.execute(
                "SELECT * FROM scheduled_tasks "
                "WHERE enabled=1"
            ).fetchall()
            for row in rows:
                task = ScheduledTask(
                    id=row[0], name=row[1],
                    instruction=row[2],
                    schedule_type=row[3],
                    schedule_time=row[4],
                    enabled=bool(row[5]),
                    last_run=row[6],
                    run_count=row[7] or 0
                )
                self._tasks[task.id] = task
                self._register_schedule(task)
        except Exception as e:
            print(f"[Scheduler] Load failed: {e}")
    
    def add_task(self, name: str,
                  instruction: str,
                  schedule_type: str,
                  schedule_time: str) -> str:
        """Add a new scheduled task."""
        import uuid
        task_id = str(uuid.uuid4())[:8]
        task = ScheduledTask(
            id=task_id,
            name=name,
            instruction=instruction,
            schedule_type=schedule_type,
            schedule_time=schedule_time
        )
        self._tasks[task_id] = task
        self._register_schedule(task)
        self._save_task(task)
        return task_id
    
    def _register_schedule(self, 
                            task: ScheduledTask):
        """Register task with schedule library."""
        def job():
            self._run_task(task)
        
        t = task.schedule_time
        st = task.schedule_type
        
        try:
            if st == "hourly":
                schedule.every().hour.do(job).tag(
                    task.id
                )
            elif st == "daily":
                schedule.every().day.at(t).do(
                    job
                ).tag(task.id)
            elif st == "weekly":
                day, time_str = t.split(" ", 1) \
                    if " " in t else ("monday", t)
                getattr(
                    schedule.every(), day
                ).at(time_str).do(job).tag(task.id)
            elif st == "once":
                schedule.every().day.at(t).do(
                    job
                ).tag(task.id)
        except Exception as e:
            print(f"[Scheduler] Register "
                  f"failed: {e}")
    
    def _run_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        print(f"[Scheduler] Running: {task.name}")
        try:
            loop = asyncio.new_event_loop()
            
            async def execute():
                from core.task_planner import (
                    task_planner
                )
                t = await task_planner.plan(
                    task.instruction
                )
                await task_planner.execute(t)
            
            loop.run_until_complete(execute())
            loop.close()
            
            task.last_run = datetime.now()\
                .isoformat()
            task.run_count += 1
            self._save_task(task)
        except Exception as e:
            print(f"[Scheduler] Task failed: {e}")
    
    def _save_task(self, task: ScheduledTask):
        try:
            conn = sqlite3.connect(
                self._db,
                check_same_thread=False
            )
            conn.execute("""
                INSERT OR REPLACE INTO 
                scheduled_tasks VALUES 
                (?,?,?,?,?,?,?,?)
            """, (
                task.id, task.name,
                task.instruction,
                task.schedule_type,
                task.schedule_time,
                int(task.enabled),
                task.last_run,
                task.run_count
            ))
            conn.commit()
        except Exception as e:
            print(f"[Scheduler] Save failed: {e}")
    
    def start(self):
        """Start the scheduler thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True
        )
        self._thread.start()
        self.start_auto_jobs()
        print("[Scheduler] ✅ Running")
    
    
    def start_auto_jobs(self):
        """Start auto reasoning on boot."""
        schedule.every(1).hours.do(
            self._run_auto_reasoning
        )
        # Run immediately on boot
        import threading
        t = threading.Thread(
            target=self._run_auto_reasoning,
            daemon=True
        )
        t.start()
        print("[Scheduler] Auto reasoning: ON "
              "(runs on boot + every 1h)")

    def _run_auto_reasoning(self):
        """Generate proactive system advisory."""
        import psutil, sqlite3, os
        from datetime import datetime
        
        print("[Scheduler] Running auto reasoning...")
        
        try:
            advisories = []
            
            # CPU check
            cpu = psutil.cpu_percent(interval=2)
            if cpu > 80:
                advisories.append(
                    f"High CPU usage: {cpu}% — "
                    f"consider closing unused apps"
                )
            
            # RAM check
            ram = psutil.virtual_memory().percent
            if ram > 85:
                advisories.append(
                    f"High RAM usage: {ram}% — "
                    f"system may slow down"
                )
            
            # Disk check
            disk = psutil.disk_usage('/').percent
            if disk > 85:
                advisories.append(
                    f"Disk {disk}% full — "
                    f"consider cleanup"
                )
            
            # Battery check
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged \
               and battery.percent < 20:
                advisories.append(
                    f"Battery low: "
                    f"{battery.percent}% — "
                    f"plug in soon"
                )
            
            # Check overdue tasks from DB
            db_path = os.path.join(
                os.path.dirname(__file__),
                "../nova_logs.db"
            )
            try:
                conn = sqlite3.connect(db_path)
                overdue = conn.execute("""
                    SELECT COUNT(*) FROM goals 
                    WHERE status='active' 
                    AND deadline < datetime('now')
                """).fetchone()[0]
                if overdue > 0:
                    advisories.append(
                        f"{overdue} overdue task(s) "
                        f"need attention"
                    )
                conn.close()
            except:
                pass
            
            # Save advisories to DB for HQ panel
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS 
                    advisories (
                        id INTEGER PRIMARY KEY,
                        message TEXT,
                        created_at TEXT,
                        severity TEXT
                    )
                """)
                # Clear old advisories
                conn.execute("DELETE FROM advisories")
                
                if advisories:
                    for adv in advisories:
                        severity = "warning"
                        if "High CPU" in adv or \
                           "High RAM" in adv:
                            severity = "warning"
                        if "Disk" in adv or \
                           "overdue" in adv:
                            severity = "critical"
                        conn.execute(
                            "INSERT INTO advisories "
                            "(message, created_at, "
                            "severity) VALUES (?,?,?)",
                            (adv, 
                             datetime.now().isoformat(),
                             severity)
                        )
                else:
                    conn.execute(
                        "INSERT INTO advisories "
                        "(message, created_at, severity)"
                        " VALUES (?,?,?)",
                        ("All systems nominal. "
                         "No issues detected.",
                         datetime.now().isoformat(),
                         "info")
                    )
                conn.commit()
                conn.close()
                print(f"[Scheduler] Reasoning complete."
                      f" {len(advisories)} advisories.")
            except Exception as e:
                print(f"[Scheduler] DB error: {e}")
        
        except Exception as e:
            print(f"[Scheduler] Reasoning error: {e}")

    def _log_task(self, task_id: str, message: str, status: str):
        """Log task execution."""
        import sqlite3, os
        from datetime import datetime
        db_path = os.path.join(os.path.dirname(__file__), "../nova_logs.db")
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS task_log (id TEXT, message TEXT, status TEXT, ran_at TEXT)"
            )
            conn.execute(
                "INSERT INTO task_log VALUES (?,?,?,?)",
                (task_id, message, status, datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
        except:
            pass

    def _run_loop(self):
        while self._running:
            schedule.run_pending()
            time.sleep(30)
    
    def get_tasks(self) -> list:
        return list(self._tasks.values())
    
    def remove_task(self, task_id: str):
        schedule.clear(task_id)
        if task_id in self._tasks:
            del self._tasks[task_id]

scheduler = TaskScheduler()
