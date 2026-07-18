import asyncio
import threading
import logging
import uvicorn
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Suppress Uvicorn's verbose startup logs to keep our summary clean
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

async def start_system():
    print("\n" + "="*50)
    print("  N.O.V.A System Boot Sequence")
    print("="*50)

    # 0. Database Schema
    try:
        def ensure_tables():
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "nova_logs.db")
            conn = sqlite3.connect(db_path, check_same_thread=False)
            
            conn.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                title TEXT DEFAULT 'Goal',
                description TEXT DEFAULT '',
                target TEXT DEFAULT '',
                progress INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                deadline DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)
            try:
                cols = [r[1] for r in conn.execute("PRAGMA table_info(goals)").fetchall()]
                if "title" not in cols:
                    conn.execute("ALTER TABLE goals ADD COLUMN title TEXT DEFAULT 'Goal'")
                if "target" not in cols:
                    conn.execute("ALTER TABLE goals ADD COLUMN target TEXT DEFAULT ''")
                if "progress" not in cols:
                    conn.execute("ALTER TABLE goals ADD COLUMN progress INTEGER DEFAULT 0")
                if "description" not in cols:
                    conn.execute("ALTER TABLE goals ADD COLUMN description TEXT DEFAULT ''")
            except Exception:
                pass
            
            conn.execute("""
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id TEXT PRIMARY KEY,
                granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                granted_by TEXT DEFAULT 'biometric'
            );
            """)
            
            conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                type TEXT,
                payload TEXT,
                priority INTEGER,
                timestamp TEXT,
                status TEXT DEFAULT 'pending'
            );
            """)
            
            conn.commit()
            conn.close()

        ensure_tables()
        print("[NOVA] ✓ Database schema verified")
    except Exception as e:
        print(f"[NOVA] ✗ Database initialization failed: {e}")

    # 1. Encryption
    try:
        from core.encryption import encryption
        _ = encryption.get_or_create_key()
        print("[NOVA] ✓ Encryption ready")
    except Exception as e:
        print(f"[NOVA] ✗ Encryption failed: {e}")

    # 2. Event Bus
    try:
        from core.event_bus import event_bus
        await event_bus.start()
        print("[NOVA] ✓ Event Bus running")
    except Exception as e:
        print(f"[NOVA] ✗ Event Bus failed: {e}")

    # Start task scheduler
    try:
        from core.scheduler import scheduler
        scheduler.start()
        print("[NOVA] ✓ Task Scheduler running")
    except Exception as e:
        print(f"[NOVA] ✗ Scheduler failed: {e}")

    # 3. System Optimizer
    try:
        from core.system_optimizer import system_optimizer
        asyncio.create_task(system_optimizer.start())
        print("[NOVA] ✓ System Optimizer running")
    except Exception as e:
        print(f"[NOVA] ✗ System Optimizer failed: {e}")

    # 4. Biometric Auth
    try:
        from core.biometric import biometric_auth
        print("[NOVA] ✓ Biometric Auth ready")
    except Exception as e:
        print(f"[NOVA] ✗ Biometric Auth failed: {e}")

    # Cowork Engines
    try:
        from core.memory_engine import memory_engine
        print("[NOVA] ✓ Memory Engine ready")
    except Exception as e:
        print(f"[NOVA] ✗ Memory Engine failed: {e}")

    try:
        from core.skill_engine import skill_engine
        print("[NOVA] ✓ Skill Engine ready")
    except Exception as e:
        print(f"[NOVA] ✗ Skill Engine failed: {e}")

    # 5. Browser
    try:
        from integrations.browser import browser
        print("[NOVA] ✓ Browser ready (lazy launch)")
    except Exception as e:
        print(f"[NOVA] ✗ Browser failed: {e}")

    try:
        from core.security_officer import security_officer
        security_officer.start_monitoring()
        print("[NOVA] ✓ Security Officer active")
    except Exception as e:
        print(f"[NOVA] ✗ Security failed: {e}")

    # 6. Controller (Part of NovaApp)
    try:
        from nova import NovaApp
        import builtins
        
        # Suppress NovaApp's verbose stdout to keep the startup UI clean requested by user,
        # but do not silence actual exceptions.
        class DummyStream:
            def write(self, *args): pass
            def flush(self, *args): pass
            def isatty(self): return False
            
        old_stdout = sys.stdout
        sys.stdout = DummyStream()
        try:
            app_container = NovaApp()
        finally:
            sys.stdout = old_stdout
            
        print("[NOVA] ✓ Controller subscribed")
    except Exception as e:
        print(f"[NOVA] ✗ Controller failed: {e}")
        app_container = None

    # Inject initialized global instances into the API server so it doesn't try to recompute them 
    try:
        from core import api_server
        from core.auth import AuthManager
        from core.health import HealthEngine
        from core.context_engine import ContextEngine
        from core.chat_engine import ChatEngine
        
        api_server.nova_app = app_container
        api_server.auth_manager = AuthManager()
        api_server.health_engine = HealthEngine()
        
        if app_container:
            api_server.context_engine = ContextEngine(
                notion_tool=app_container.notion_tool,
                expense_manager=app_container.expense_manager,
                daemon=None,
                health_engine=api_server.health_engine
            )
            api_server.chat_engine = ChatEngine(
                controller=app_container.controller,
                health_engine=api_server.health_engine,
                context_engine=api_server.context_engine
            )
    except Exception as e:
        pass

    # 7. Daemon with supervisor (auto-restart on crash)
    try:
        if app_container:
            from core.daemon import NovaDaemon
            import time as _time
            from collections import deque

            # Capture the main event loop so the daemon publishes onto it
            # instead of creating a competing loop
            main_loop = asyncio.get_running_loop()
            api_server.main_loop = main_loop

            daemon = NovaDaemon(
                memory_tool=app_container.memory_tool,
                notion_tool=app_container.notion_tool,
                pdf_tool=app_container.pdf_tool,
                event_loop=main_loop
            )
            api_server.daemon = daemon
            api_server.context_engine.daemon = daemon

            def _daemon_supervisor():
                """Supervise the daemon thread: respawn on crash, rate-limited."""
                MAX_RESTARTS = 5
                WINDOW_SECONDS = 600  # 10 minutes
                restart_times = deque(maxlen=MAX_RESTARTS)

                while True:
                    daemon.running = False  # reset state before each launch
                    t = threading.Thread(target=daemon.run, args=(False,), daemon=True)
                    t.start()
                    api_server.daemon_thread = t
                    t.join()  # blocks until daemon.run() exits

                    # If we get here, the daemon thread has exited
                    now = _time.time()
                    last_err = daemon.last_error or "unknown"
                    print(f"[NOVA] ⚠ Daemon exited. Last error:\n{last_err}")

                    # Rate-limit restarts
                    restart_times.append(now)
                    if len(restart_times) >= MAX_RESTARTS:
                        oldest = restart_times[0]
                        if now - oldest < WINDOW_SECONDS:
                            print(f"[NOVA] ✗ Daemon crashed {MAX_RESTARTS} times in "
                                  f"{int(now - oldest)}s — giving up. Manual restart required.")
                            break

                    backoff = 5
                    print(f"[NOVA] ↻ Restarting daemon in {backoff}s...")
                    _time.sleep(backoff)

            supervisor_thread = threading.Thread(target=_daemon_supervisor, daemon=True)
            supervisor_thread.start()
            print("[NOVA] ✓ Daemon running (supervised)")
    except Exception as e:
        print(f"[NOVA] ✗ Daemon failed: {e}")

    # Voice interface is available but OFF by default
    try:
        # Pre-import to ensure it's ready for toggle
        from core.voice_daemon import voice_daemon
        print("[NOVA] Voice interface ready (Default: OFF)")
    except Exception as e:
        print(f"[NOVA] Voice unavailable: {e}")

    # Start reminder daemon (async background task)
    try:
        from core.reminder_daemon import reminder_loop
        asyncio.create_task(reminder_loop())
        print("[NOVA] ✓ Reminder daemon running")
    except Exception as e:
        print(f"[NOVA] ✗ Reminder daemon failed: {e}")

    # Start automated morning briefing scheduler
    try:
        from core.briefing_scheduler import start_briefing_scheduler
        async def send_briefing_to_dashboard(text: str):
            from core.event_bus import event_bus, NovaEvent
            await event_bus.publish(NovaEvent(
                source="scheduler",
                type="morning_briefing",
                payload={"message": text},
                priority=8
            ))
        asyncio.create_task(start_briefing_scheduler(send_briefing_to_dashboard))
        print("[NOVA] ✓ Briefing scheduler running")
    except Exception as e:
        print(f"[NOVA] ✗ Briefing scheduler failed: {e}")

    # Start System Resource Monitor
    try:
        from core.resource_monitor import start_resource_monitor
        async def send_stats_to_dashboard(event_type: str, stats: dict):
            from core.event_bus import event_bus, NovaEvent
            await event_bus.publish(NovaEvent(
                source="resource_monitor",
                type=event_type,
                payload=stats,
                priority=5
            ))
        asyncio.create_task(start_resource_monitor(send_stats_to_dashboard))
        print("[NOVA] ✓ Resource monitor running")
    except Exception as e:
        print(f"[NOVA] ✗ Resource monitor failed: {e}")

    # 8. API Server
    print("[NOVA] ✓ API Server live on localhost:8000")
    print("="*50 + "\n")


from contextlib import asynccontextmanager

@asynccontextmanager
async def _dummy_lifespan(app):
    yield

async def main():
    await start_system()
    
    from core.api_server import app
    # Override the default heavy lifespan with a dummy to prevent double startup
    app.router.lifespan_context = _dummy_lifespan
    
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    import signal
    import sys
    
    def handle_sigint(sig, frame):
        print("\n[NOVA] Shutdown requested. Goodbye.")
        os._exit(0)
        
    signal.signal(signal.SIGINT, handle_sigint)
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[NOVA] Fatal error: {e}")
