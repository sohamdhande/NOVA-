
import signal
import sys
import time
from core.watcher import InboxWatcher
from core.telemetry import TelemetryLogger

class NovaDaemon:
    def __init__(self):
        self.running = False
        self.watcher = InboxWatcher()
        self.telemetry = TelemetryLogger()

    def run(self):
        """Start the daemon loop."""
        print("[NOVA] Starting background daemon (Ctrl+C to stop)...")
        print("[NOVA] Monitoring inbox/ in SAFE MODE.")
        
        self.running = True
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

        last_heartbeat = 0
        scan_interval = 10
        
        while self.running:
            try:
                current_time = time.time()
                
                # 1. Heartbeat every 60s
                if current_time - last_heartbeat > 60:
                    self.telemetry.increment("daemon_heartbeat")
                    last_heartbeat = current_time
                    # Optional: print specific status if needed, but keep log clean
                    
                # 2. Scan Inbox (Safe Mode)
                # We use safe_mode=True to ensure high-risk actions are queued
                report = self.watcher.scan(safe_mode=True)
                if report != "Inbox is empty.":
                    print(f"[Daemon] {report}")

                # Sleep until next scan
                time.sleep(scan_interval)

            except Exception as e:
                print(f"[Daemon] Error: {e}")
                time.sleep(5)  # Backoff on error

        print("[NOVA] Daemon stopped gracefully.")

    def _handle_exit(self, signum, frame):
        print("\n[NOVA] Stopping daemon...")
        self.running = False
