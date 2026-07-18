import asyncio
from datetime import datetime, timedelta
import pytz

from tools.calendar_tool import CalendarTool
from tools.weather_tool import get_weather
from llm import generate_summary
from core.personality import get_system_prefix

async def wait_until_7am():
    """Calculate seconds until next 7:00 AM IST and sleep."""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    target = now.replace(hour=7, minute=0, second=0, microsecond=0)
    
    if now >= target:
        target += timedelta(days=1)
        
    seconds_until_7am = (target - now).total_seconds()
    print(f"[BriefingScheduler] Waiting {seconds_until_7am:.0f} seconds until next 7 AM IST.")
    await asyncio.sleep(seconds_until_7am)

async def run_morning_briefing(send_to_dashboard):
    """Fetch data, build context, generate summary, and push via WS."""
    print("[BriefingScheduler] Running morning briefing...")
    
    try:
        # 1. Fetch Calendar Events
        cal = CalendarTool()
        cal_res = cal.get_today_events()
        today_events = cal_res.get("data", []) if cal_res.get("status") == "success" else []
        
        # 2. Fetch Weather
        weather_result = await get_weather("Pune")
        
        # 3. Build Context
        context = {
            "events": today_events,
            "tasks": [],
            "weather": weather_result
        }
        
        # 4. Generate Summary
        briefing_text = generate_summary(context)
        
        # 5. Push to Dashboard
        await send_to_dashboard(briefing_text)
        
        # 6. Log to SQLite
        import sqlite3
        import os
        from contextlib import closing
        
        db_path = os.path.expanduser('~/nova_logs.db')
        try:
            with closing(sqlite3.connect(db_path)) as conn:
                with closing(conn.cursor()) as cursor:
                    cursor.execute('''CREATE TABLE IF NOT EXISTS audit_logs
                                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                       timestamp TEXT,
                                       action TEXT,
                                       details TEXT)''')
                    cursor.execute(
                        "INSERT INTO audit_logs (timestamp, action, details) VALUES (?, ?, ?)",
                        (datetime.now().isoformat(), "morning_briefing", "Auto morning briefing sent at 7 AM")
                    )
                    conn.commit()
        except Exception as e:
            print(f"[BriefingScheduler] Failed to log to SQLite: {e}")
            
    except Exception as e:
        print(f"[BriefingScheduler] Failed to run briefing: {e}")

async def start_briefing_scheduler(send_to_dashboard):
    """Infinite loop pulling briefing at 7 AM."""
    print("[NOVA] ✓ Briefing scheduler started")
    while True:
        await wait_until_7am()
        await run_morning_briefing(send_to_dashboard)
        await asyncio.sleep(60)  # prevent double trigger inside the same minute
