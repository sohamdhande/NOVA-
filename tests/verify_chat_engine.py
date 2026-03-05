#!/usr/bin/env python3
"""
verify_chat_engine.py — test harness for ChatEngine.

Scenarios:
  1. Simple status query → compact mode
  2. Task list query → expanded mode
  3. Simulation mode → projection returned
  4. Tone adaptation (stable vs critical)
  5. Projection field present after mutation-like status
  6. Context lock / unlock commands
  7. Client command routing (e.g. "open tasks")

Does NOT require a running controller — uses a mock.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chat_engine import ChatEngine

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
    tag = "PASS" if condition else "FAIL"
    extra = f"  ({detail})" if detail else ""
    print(f"  [{tag}] {name}{extra}")


# ------------------------------------------------------------------ #
#  Mock Controller                                                     #
# ------------------------------------------------------------------ #

class MockController:
    """Deterministic mock for Controller.handle_command."""

    def handle_command(self, command: str):
        cmd = command.lower().strip()

        if "show tasks" in cmd or "read_open" in cmd:
            return {
                "intent": "task",
                "domain": "notion",
                "action": "read_open",
                "risk": "low",
                "status": "success",
                "response": "Found 3 tasks:\n- Finish paper\n- Review PR\n- Deploy service",
            }

        if "create task" in cmd:
            return {
                "intent": "task",
                "domain": "notion",
                "action": "create_task",
                "risk": "high",
                "status": "success",
                "response": "Task created: Test Task",
            }

        if "delete" in cmd:
            return {
                "intent": "task",
                "domain": "notion",
                "action": "update_task",
                "risk": "high",
                "status": "blocked",
                "response": "Daily limit exceeded for 'update_task' (10/10).",
            }

        return {
            "intent": "information",
            "domain": "system",
            "action": "none",
            "risk": "low",
            "status": "success",
            "response": "System operational.",
        }


class MockHealthEngine:
    @staticmethod
    def _compute_raw_health(metrics):
        return 85.0

    def calculate_health(self, metrics):
        return {"system_health": 90, "health_zone": "stable", "health_trigger": False}


class MockHealthEngineCritical:
    @staticmethod
    def _compute_raw_health(metrics):
        return 40.0

    def calculate_health(self, metrics):
        return {"system_health": 50, "health_zone": "critical", "health_trigger": True}


def default_metrics():
    return {
        "overdue_count": 0,
        "deadlines_48h": 0,
        "deadlines_24h": 0,
        "active_tasks": 5,
        "expense_logged_today": True,
        "missed_days_this_month": 0,
        "last_7_day_streak": True,
        "daemon_crash_recent": False,
        "daemon_uptime_hours": 50,
    }


# ------------------------------------------------------------------ #
#  Test 1 — Simple Status Query (compact)                              #
# ------------------------------------------------------------------ #

def test_simple_status():
    print("\n[Test 1] Simple Status Query")
    engine = ChatEngine(MockController(), MockHealthEngine(), None)
    r = engine.handle_message(
        "what is the system status",
        current_health_data={"system_health": 95, "health_zone": "stable"},
        current_metrics=default_metrics(),
    )
    check("status is success", r["status"] == "success")
    check("message exists", len(r["message"]) > 0)
    check("response_mode is compact", r["response_mode"] == "compact",
          f"got {r['response_mode']}")
    check("structured is None", r["structured"] is None)
    check("projection is None", r["projection"] is None)


# ------------------------------------------------------------------ #
#  Test 2 — Task List Query (expanded)                                 #
# ------------------------------------------------------------------ #

def test_task_list():
    print("\n[Test 2] Task List Query (expanded)")
    engine = ChatEngine(MockController(), MockHealthEngine(), None)
    r = engine.handle_message(
        "show tasks",
        current_health_data={"system_health": 95, "health_zone": "stable"},
        current_metrics=default_metrics(),
    )
    check("status is success", r["status"] == "success")
    check("structured is task_list", r["structured"] is not None and r["structured"]["type"] == "task_list",
          f"got {r.get('structured')}")
    if r["structured"]:
        check("has 3 items", len(r["structured"]["items"]) == 3)
    check("response_mode is expanded", r["response_mode"] == "expanded")


# ------------------------------------------------------------------ #
#  Test 3 — Simulation Mode                                            #
# ------------------------------------------------------------------ #

def test_simulation():
    print("\n[Test 3] Simulation Mode")
    engine = ChatEngine(MockController(), MockHealthEngine(), None)
    r = engine.handle_message(
        "simulate create task finish homework",
        current_health_data={"system_health": 90, "health_zone": "stable"},
        current_metrics=default_metrics(),
    )
    check("status is info", r["status"] == "info")
    check("projection present", r["projection"] is not None)
    if r["projection"]:
        check("current_health in projection", "current_health" in r["projection"])
        check("projected_health in projection", "projected_health" in r["projection"])
    check("trace has simulation", any("simulation" in t for t in r["trace"]))


# ------------------------------------------------------------------ #
#  Test 4 — Tone Adaptation (stable vs critical)                       #
# ------------------------------------------------------------------ #

def test_tone_adaptation():
    print("\n[Test 4] Tone Adaptation")

    # Stable
    engine_s = ChatEngine(MockController(), MockHealthEngine(), None)
    rs = engine_s.handle_message(
        "what is the system status",
        current_health_data={"system_health": 95, "health_zone": "stable"},
        current_metrics=default_metrics(),
    )
    check("stable: message has 'stable'", "stable" in rs["message"].lower(),
          f"msg: {rs['message'][:60]}")

    # Critical
    engine_c = ChatEngine(MockController(), MockHealthEngineCritical(), None)
    rc = engine_c.handle_message(
        "what is the system status",
        current_health_data={"system_health": 50, "health_zone": "critical"},
        current_metrics=default_metrics(),
    )
    check("critical: message has 'action required'",
          "action required" in rc["message"].lower(),
          f"msg: {rc['message'][:60]}")


# ------------------------------------------------------------------ #
#  Test 5 — Projection After Mutation                                  #
# ------------------------------------------------------------------ #

def test_projection():
    print("\n[Test 5] Projection After Mutation")
    engine = ChatEngine(MockController(), MockHealthEngine(), None)
    r = engine.handle_message(
        "create task test item",
        current_health_data={"system_health": 90, "health_zone": "stable"},
        current_metrics=default_metrics(),
    )
    check("status is success", r["status"] == "success")
    check("projection present", r["projection"] is not None,
          f"projection={r.get('projection')}")
    if r["projection"]:
        check("current_health == 90", r["projection"]["current_health"] == 90)


# ------------------------------------------------------------------ #
#  Test 6 — Context Lock Command                                       #
# ------------------------------------------------------------------ #

def test_context_lock():
    print("\n[Test 6] Context Lock / Unlock")
    engine = ChatEngine(MockController(), MockHealthEngine(), None)

    # Lock
    r1 = engine.handle_message(
        "lock context finance",
        current_health_data={"system_health": 95, "health_zone": "stable"},
    )
    check("lock: status success", r1["status"] == "success")
    check("lock: message mentions 'finance'", "finance" in r1["message"].lower())
    check("lock: internal state set", engine._context_lock == "finance")

    # Unlock
    r2 = engine.handle_message(
        "unlock context",
        current_health_data={"system_health": 95, "health_zone": "stable"},
    )
    check("unlock: status success", r2["status"] == "success")
    check("unlock: internal state cleared", engine._context_lock is None)


# ------------------------------------------------------------------ #
#  Test 7 — Client Command Routing                                     #
# ------------------------------------------------------------------ #

def test_client_command():
    print("\n[Test 7] Client Command Routing")
    engine = ChatEngine(MockController(), MockHealthEngine(), None)
    r = engine.handle_message(
        "open tasks",
        current_health_data={"system_health": 95, "health_zone": "stable"},
    )
    check("status is success", r["status"] == "success")
    check("structured is client_command", r["structured"] is not None and
          r["structured"].get("type") == "client_command")
    if r["structured"]:
        check("target is tasks", r["structured"].get("target") == "tasks")
    check("response_mode is expanded", r["response_mode"] == "expanded")


# ------------------------------------------------------------------ #
#  Runner                                                              #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    print("=" * 60)
    print("  NOVA Chat Engine — Verification Suite")
    print("=" * 60)

    test_simple_status()
    test_task_list()
    test_simulation()
    test_tone_adaptation()
    test_projection()
    test_context_lock()
    test_client_command()

    print("\n" + "=" * 60)
    print(f"  RESULTS: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)
