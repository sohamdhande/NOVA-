"""
NOVA - Autonomous Productivity Operator
Production-grade application container with persistent lifecycle.
"""

import json
import subprocess
import os
import sys
from datetime import datetime
from typing import Optional

# Import all subsystems
from controller import Controller
from storage.logger import ExecutionLogger
from core.telemetry import TelemetryLogger
from core.guardrail import MutationGuardrail
from storage.vector_store import VectorStore
from storage.memory_store import MemoryStore
from tools.memory_tool import MemoryTool
from tools.calendar_tool import CalendarTool
from tools.notion_tool import NotionTool
from tools.pdf_tool import PDFTool
from core.system_tool import SystemTool
from core.priority_engine import PriorityEngine


class NovaApp:
    """
    Main application container for NOVA.
    
    Initializes all heavy subsystems once and maintains them
    throughout the process lifecycle.
    
    This structure enables:
    - Single model load per process
    - Proper dependency injection
    - Clean separation of concerns
    - Future daemon/API server modes
    """
    
    def __init__(self):
        """Initialize all subsystems once."""
        print("=" * 60)
        print("  NOVA - Initializing Application Container")
        print("=" * 60)
        
        # Core infrastructure
        print("[1/7] Initializing logger...")
        self.logger = ExecutionLogger()
        
        print("[2/7] Initializing telemetry...")
        self.telemetry = TelemetryLogger()
        
        print("[3/7] Initializing guardrail...")
        self.guardrail = MutationGuardrail()
        
        # Memory subsystem (heavy - loads embedding model)
        print("[4/7] Initializing vector store (loading embedding model)...")
        self.vector_store = VectorStore()
        
        print("[5/7] Initializing memory store...")
        self.memory_store = MemoryStore(self.vector_store)
        
        # Tools (lightweight - just API clients)
        print("[6/7] Initializing tools...")
        self.memory_tool = MemoryTool(self.memory_store)
        self.calendar_tool = CalendarTool()
        self.notion_tool = NotionTool()
        self.pdf_tool = PDFTool()
        self.system_tool = SystemTool()
        
        # Controller (orchestration layer)
        print("[7/7] Initializing controller...")
        self.controller = Controller(
            logger=self.logger,
            telemetry=self.telemetry,
            guardrail=self.guardrail,
            memory_tool=self.memory_tool,
            calendar_tool=self.calendar_tool,
            notion_tool=self.notion_tool,
            pdf_tool=self.pdf_tool,
            system_tool=self.system_tool
        )

        # Priority Engine
        print("[8/8] Initializing Priority Engine...")
        self.priority_engine = PriorityEngine()

        # Expense Manager
        print("[9/9] Initializing Expense Manager...")
        from core.expense import ExpenseManager
        self.expense_manager = ExpenseManager()
        
        print("\n" + "=" * 60)
        print("  ✓ NOVA online. All subsystems ready.")
        print("=" * 60)
    
    def speak(self, text: str):
        """Text-to-speech output."""
        try:
            subprocess.run(["say", text], check=False)
        except Exception as e:
            print(f"[Voice Error]: {e}")
    
    def show_logs(self):
        """Display recent execution logs."""
        logs = self.logger.get_recent_logs(5)
        
        if not logs:
            print("No execution logs found.")
            return
        
        print("\n" + "=" * 50)
        print("  RECENT EXECUTION LOGS")
        print("=" * 50)
        
        for log in logs:
            log_id, timestamp, command, intent, domain, action, risk, status, summary = log
            print(f"\n  [{log_id}] {timestamp}")
            print(f"  Command : {command}")
            print(f"  Intent  : {intent}  |  Domain: {domain}")
            print(f"  Action  : {action}")
            print(f"  Risk    : {risk}  |  Status: {status}")
            print(f"  Response: {summary[:100]}{'...' if len(summary) > 100 else ''}")
            print("-" * 50)
    
    def show_telemetry(self):
        """Display telemetry statistics."""
        stats = self.telemetry.get_summary(days=1)
        print("\n--- DAILY TELEMETRY ---")
        for k, v in stats.items():
            print(f"{k}: {v}")
        print("-----------------------\n")
    
    def cleanup_memory_duplicates(self):
        """Run duplicate cleanup on vector store."""
        print("\n[NOVA] Running duplicate cleanup...")
        removed = self.vector_store.cleanup_duplicates()
        print(f"[NOVA] Cleanup complete. Removed {removed} duplicate(s).\n")
    
    def scan_inbox(self):
        """Scan email inbox for actionable items."""
        from core.watcher import InboxWatcher
        print("[NOVA] Scanning inbox...")
        watcher = InboxWatcher()
        report = watcher.scan()
        print(report)
    
    def start_daemon(self):
        """Start background daemon mode."""
        from core.daemon import NovaDaemon
        daemon = NovaDaemon(
            memory_tool=self.memory_tool,
            notion_tool=self.notion_tool,
            pdf_tool=self.pdf_tool
        )
        daemon.run()
    
    def process_queue(self):
        """Process pending action queue."""
        queue_file = os.path.join(os.path.dirname(__file__), "queue/pending.json")
        
        if not os.path.exists(queue_file):
            print("[NOVA] No pending actions.")
            return
        
        with open(queue_file, "r") as f:
            queue = json.load(f)
        
        if not queue:
            print("[NOVA] Queue is empty.")
            return
        
        print(f"\n[NOVA] Found {len(queue)} pending actions:")
        remaining_queue = []
        
        for i, item in enumerate(queue):
            print(f"\nItem {i+1}: {item['description']}")
            print(f"Data: {item['data']}")
            choice = input("Execute this action? (y/n/skip): ").lower()
            
            if choice == "y":
                try:
                    if item["type"] == "notion":
                        self.notion_tool.create_task(title=item["data"].get("title"))
                        print("  -> Success")
                    else:
                        print(f"  -> Unknown action type: {item['type']}")
                except Exception as e:
                    print(f"  -> Error: {e}")
            elif choice == "skip":
                remaining_queue.append(item)
                print("  -> Skipped")
            else:
                print("  -> Discarded")
        
        # Save remaining
        with open(queue_file, "w") as f:
            json.dump(remaining_queue, f, indent=2)
        print("\n[NOVA] Queue processing complete.\n")
    
    def handle_confirmation(self, command: str, result: dict):
        """Handle user confirmation for high-risk actions."""
        # Print action description without the "Confirm?" suffix
        msg = result['response'].replace("Confirm? (yes/no)", "").strip()
        print(f"\n⚠  {msg}")
        
        # Show completed steps if this is a multi-step pause
        prior = result.get("step_results", [])
        if prior:
            print(f"\n  Completed {len(prior)} step(s) before this:")
            for j, r in enumerate(prior):
                print(f"    Step {j + 1}: [{r['status']}] {r['response'][:80]}")
        
        # Flush any stray input left in terminal buffer
        import termios
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
        
        while True:
            confirm = input("Confirm? (yes/no) > ").strip().lower()
            
            if confirm == "yes":
                print("[NOVA] Executing confirmed action...")
                if result.get("confirm_type") == "multi_step":
                    response = self.controller.execute_confirmed_step(command, result)
                else:
                    response = self.controller.execute_confirmed_action(command, result)
                print(response)
                self.speak(response)
                return
            elif confirm == "no":
                print("[NOVA] Action cancelled.")
                self.controller.cancel_confirmed_action(command, result)
                self.speak("Action cancelled.")
                return
            elif confirm == "":
                continue  # Ignore empty input
            else:
                print("[NOVA] Please type 'yes' or 'no'.")
    
    def run_cli(self):
        """Main CLI loop - runs until interrupted."""
        try:
            while True:
                print("\n" + "-" * 50)
                command = input("NOVA > ").strip()
                
                # -----------------------------------------------------------
                # CRITICAL: EMPTY INPUT SAFETY GATE
                # -----------------------------------------------------------
                # No planner invocation, no telemetry, no memory calls
                if not command:
                    continue
                
                # Handle special CLI commands
                if command.lower() == "show logs":
                    self.show_logs()
                    continue
                
                if command.lower() == "telemetry stats":
                    self.show_telemetry()
                    continue
                
                if command.lower() == "cleanup duplicates":
                    self.cleanup_memory_duplicates()
                    continue
                
                if command.lower() == "scan inbox":
                    self.scan_inbox()
                    continue
                
                if command.lower() == "start daemon":
                    self.start_daemon()
                    continue
                
                if command.lower() == "process queue":
                    self.process_queue()
                    continue
                
                if command.lower() == "show priorities":
                    self.show_priorities()
                    continue
                
                if command.lower() in ("exit", "quit"):
                    print("\nNOVA offline.")
                    break
                
                # Execute command through controller
                result = self.controller.handle_command(command)
                
                # Only show execution report in DEBUG mode
                import config
                if config.DEBUG:
                    print("\n--- EXECUTION REPORT ---")
                    print(json.dumps(result, indent=2))
                    print("--- END REPORT ---\n")
                
                # Check if confirmation is required
                if result.get("requires_confirmation"):
                    self.handle_confirmation(command, result)
                    continue
                
                # Display per-step results for multi-step commands
                step_results = result.get("step_results")
                if step_results:
                    print(f"\n  [{len(step_results)} step(s) executed]")
                    for j, r in enumerate(step_results):
                        status_icon = "✓" if r["status"] == "success" else "✗"
                        print(f"    {status_icon} Step {j + 1} [{r['domain']}/{r['action']}]: {r['response'][:100]}")
                
                final_response = result["response"]
                print(final_response)
                self.speak(final_response)
                
        except KeyboardInterrupt:
            print("\n\nNOVA offline.")
        except Exception as e:
            print(f"\n✗ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def show_priorities(self):
        """Fetch tasks, calculate priorities, and display."""
        print("\n[NOVA] Fetching active tasks from Notion...")
        
        # 1. Fetch tasks
        # Use existing notion_tool to get tasks
        # We need a method that gets tasks. read_open_tasks returns a dict with 'data' list.
        response = self.notion_tool.read_open_tasks(limit=50)
        if response.get("status") != "success":
            print(f"Error fetching tasks: {response.get('message')}")
            return
            
        tasks = response.get("data", [])
        if not tasks:
            print("No active tasks found.")
            return

        print(f"[NOVA] analyzing {len(tasks)} tasks...")

        # 2. Process with Priority Engine
        # TODO: Retrieve actual operational mode from SystemTool or Config
        context = {
            "goal_weight": 1, # Default weight
            "mode": "normal"
        }
        
        start_t = datetime.now()
        prioritized = self.priority_engine.process_tasks(tasks, context=context)
        end_t = datetime.now()
        
        # 3. Display
        print("\n" + "=" * 80)
        print(f"  PRIORITY QUEUE ({len(prioritized)} tasks) - Calculated in {(end_t - start_t).total_seconds():.3f}s")
        print("=" * 80)
        print(f"{'SCORE':<8} | {'DUE DATE':<12} | {'TASK TITLE':<40} | {'TOP FACTOR'}")
        print("-" * 80)
        
        for task in prioritized[:15]: # Show top 15
            score = task['computed_score']
            title = task['title'][:38] + ".." if len(task['title']) > 38 else task['title']
            
            # Format due date
            due = "No Date"
            if task.get("due_date"):
                # Simplify for display
                try:
                    dt = datetime.fromisoformat(task.get("due_date").replace('Z', '+00:00'))
                    due = dt.strftime("%Y-%m-%d")
                except:
                    due = "Invalid"
            
            # Top breakdown factor
            breakdown = task.get("breakdown", [])
            top_factor = breakdown[0] if breakdown else ""
            
            print(f"{score:<8} | {due:<12} | {title:<40} | {top_factor}")
            
        if len(prioritized) > 15:
            print(f"... and {len(prioritized) - 15} more.")
        print("-" * 80 + "\n")


def speak(text):
    """Legacy compatibility function."""
    try:
        subprocess.run(["say", text])
    except Exception as e:
        print(f"[Voice Error]: {e}")




def show_logs():
    """Legacy compatibility function - deprecated."""
    print("[Deprecated] Use NovaApp.show_logs() instead")


def handle_confirmation(command, result):
    """Legacy compatibility function - deprecated."""
    print("[Deprecated] Use NovaApp.handle_confirmation() instead")


def main():
    """Application entrypoint."""
    app = NovaApp()
    app.run_cli()


if __name__ == "__main__":
    main()
