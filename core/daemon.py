import signal
import sys
import time
import threading
import traceback
import asyncio
from datetime import datetime
from core.watcher import InboxWatcher
from core.telemetry import TelemetryLogger
from core.briefing import BriefingEngine
from core.event_bus import event_bus, NovaEvent
from core.system_optimizer import system_optimizer

class NovaDaemon:
    def __init__(self, memory_tool, notion_tool, pdf_tool):
        self.running = False
        self.last_error = None
        self.start_time = None
        self.memory_tool = memory_tool
        self.notion_tool = notion_tool
        self.pdf_tool = pdf_tool
        self.system_optimizer = system_optimizer
        
        self.watcher = InboxWatcher(
            memory_tool=self.memory_tool,
            notion_tool=self.notion_tool,
            pdf_tool=self.pdf_tool
        )
        self.telemetry = TelemetryLogger()
        self.briefing = BriefingEngine()

    def get_uptime_hours(self) -> float:
        """Return daemon uptime in hours, or 0 if not started."""
        if self.start_time is None:
            return 0.0
        return (time.time() - self.start_time) / 3600.0

    def run(self, handle_signals=True):
        """Start the daemon loop."""
        self.start_time = time.time()
        print(f"[NOVA] Starting background daemon (handle_signals={handle_signals})...")
        print("[NOVA] Monitoring inbox/ in SAFE MODE.")
        
        self.running = True
        
        if handle_signals:
            signal.signal(signal.SIGINT, self._handle_exit)
            signal.signal(signal.SIGTERM, self._handle_exit)

        # Setup Event Bus Loop for threaded daemon
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            threading.Thread(target=loop.run_forever, daemon=True).start()

        asyncio.run_coroutine_threadsafe(event_bus.start(), loop)
        asyncio.run_coroutine_threadsafe(system_optimizer.start(), loop)
        
        # Publish daemon started
        asyncio.run_coroutine_threadsafe(event_bus.publish(NovaEvent(
            source="daemon",
            type="daemon_started",
            payload={"timestamp": datetime.utcnow().isoformat() + "Z"},
            priority=3
        )), loop)

        last_heartbeat = 0
        last_telemetry_sync = 0
        scan_interval = 10
        
        try:
            while self.running:
                try:
                    current_time = time.time()
                    
                    # 1. Heartbeat every 60s
                    if current_time - last_heartbeat > 60:
                        self.telemetry.increment("daemon_heartbeat")
                        last_heartbeat = current_time
                        
                        # Check for Morning Briefing
                        self.briefing.run_daily_check()

                    # Telemetry Sync every 5 minutes (300s)
                    if current_time - last_telemetry_sync > 300:
                        last_telemetry_sync = current_time
                        snapshot = self.telemetry.get_summary()
                        asyncio.run_coroutine_threadsafe(event_bus.publish(NovaEvent(
                            source="daemon",
                            type="telemetry_synced",
                            payload={"snapshot": snapshot},
                            priority=2
                        )), loop)
                        
                    # 2. Scan Inbox (Safe Mode)
                    # We use safe_mode=True to ensure high-risk actions are queued
                    report_data = self.watcher.scan(safe_mode=True)
                    if report_data.get("status") != "empty":
                        message = report_data.get("message", "")
                        print(f"[Daemon]\n{message}")
                        
                        processed_files = report_data.get("processed_files", [])
                        if processed_files:
                            first_file = processed_files[0].get("filename", "Unknown Item")
                            
                            # New email/file detected
                            asyncio.run_coroutine_threadsafe(event_bus.publish(NovaEvent(
                                source="daemon",
                                type="email_received",
                                payload={
                                    "subject": f"File Processed: {first_file}",
                                    "sender": "local_watcher",
                                    "preview": message[:100]
                                },
                                priority=6
                            )), loop)

                    # Sleep until next scan (interruptible)
                    for _ in range(scan_interval):
                        if not self.running:
                            break
                        time.sleep(1)

                except Exception as inner_e:
                    # Allow fatal errors to bubble up
                    # "Just report failure cleanly."
                    raise inner_e

        except Exception as e:
            self.running = False
            self.last_error = traceback.format_exc()
            print(f"[NOVA] Daemon CRASHED: {e}")
            print(self.last_error)
            
        print("[NOVA] Daemon stopped.")
        print("[NOVA] Daemon stopped gracefully.")

    def stop(self):
        """Stop the daemon loop."""
        print("[NOVA] Stopping daemon...")
        self.running = False

    def _handle_exit(self, signum, frame):
        self.stop()
