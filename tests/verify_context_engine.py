#!/usr/bin/env python3
"""
verify_context_engine.py — test harness for ContextEngine.

Scenarios:
  1. Morning trigger (hour 08–10, first of day)
  2. Deadline pressure (deadlines_24h >= 2)
  3. Discipline risk (hour >= 21, no expense)
  4. Cooldown enforcement (2h gap)
  5. Daily max enforcement (max 3/day)
  6. No duplicate firing (same conditions, within gap)

Uses temp SQLite DB.
"""

import os
import sys
import tempfile
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.context_engine import ContextEngine

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


def make_snapshot(**overrides):
    """Build a default healthy snapshot, then apply overrides."""
    base = {
        "health": 95,
        "zone": "stable",
        "health_trigger": False,
        "overdue_count": 0,
        "deadlines_24h": 0,
        "deadlines_48h": 0,
        "active_tasks": 5,
        "expense_logged_today": True,
        "missed_days_month": 0,
        "daemon_uptime_hours": 50,
        "hour_of_day": 14,
        "recent_activity_flag": True,
    }
    base.update(overrides)
    return base


def fresh_engine():
    tmp = tempfile.mktemp(suffix=".db")
    engine = ContextEngine(db_path=tmp)
    return engine, tmp


# ------------------------------------------------------------------ #
#  Test 1 — Morning Trigger                                            #
# ------------------------------------------------------------------ #

def test_morning_trigger():
    print("\n[Test 1] Morning Trigger")
    engine, tmp = fresh_engine()

    snap = make_snapshot(hour_of_day=9)
    morning_time = datetime.now().replace(hour=9, minute=0, second=0)

    result = engine.evaluate(snap, now=morning_time)
    check("triggered", result["triggered"] is True)
    check("type is morning", result["payload"]["type"] == "morning",
          f"got {result['payload']['type']}" if result["payload"] else "no payload")
    check("severity is info", result["payload"]["severity"] == "info")
    check("message exists", len(result["payload"]["message"]) > 0)
    check("recommendations is list", isinstance(result["payload"]["recommendations"], list))

    os.unlink(tmp)


# ------------------------------------------------------------------ #
#  Test 2 — Deadline Pressure                                          #
# ------------------------------------------------------------------ #

def test_deadline_pressure():
    print("\n[Test 2] Deadline Pressure")
    engine, tmp = fresh_engine()

    snap = make_snapshot(deadlines_24h=3, hour_of_day=14)
    now = datetime.now().replace(hour=14, minute=0)

    result = engine.evaluate(snap, now=now)
    check("triggered", result["triggered"] is True)
    check("type is deadline", result["payload"]["type"] == "deadline",
          f"got {result['payload']['type']}" if result["payload"] else "no payload")

    os.unlink(tmp)


# ------------------------------------------------------------------ #
#  Test 3 — Discipline After 21:00                                     #
# ------------------------------------------------------------------ #

def test_discipline():
    print("\n[Test 3] Discipline After 21:00")
    engine, tmp = fresh_engine()

    snap = make_snapshot(hour_of_day=21, expense_logged_today=False)
    now = datetime.now().replace(hour=21, minute=30)

    result = engine.evaluate(snap, now=now)
    check("triggered", result["triggered"] is True)
    check("type is discipline", result["payload"]["type"] == "discipline",
          f"got {result['payload']['type']}" if result["payload"] else "no payload")

    os.unlink(tmp)


# ------------------------------------------------------------------ #
#  Test 4 — Cooldown Enforcement (2h gap)                              #
# ------------------------------------------------------------------ #

def test_cooldown():
    print("\n[Test 4] Cooldown Enforcement")
    engine, tmp = fresh_engine()

    snap = make_snapshot(deadlines_24h=3, hour_of_day=14)
    t1 = datetime.now().replace(hour=14, minute=0)

    r1 = engine.evaluate(snap, now=t1)
    check("first fires", r1["triggered"] is True)

    # Same conditions, 30 min later (< 2h gap)
    t2 = t1 + timedelta(minutes=30)
    r2 = engine.evaluate(snap, now=t2)
    check("second suppressed (<2h)", r2["triggered"] is False)

    # After 2h gap
    t3 = t1 + timedelta(hours=2, minutes=1)
    r3 = engine.evaluate(snap, now=t3)
    check("third fires (>2h)", r3["triggered"] is True)

    os.unlink(tmp)


# ------------------------------------------------------------------ #
#  Test 5 — Daily Max Enforcement (max 3/day)                          #
# ------------------------------------------------------------------ #

def test_daily_max():
    print("\n[Test 5] Daily Max Enforcement")
    engine, tmp = fresh_engine()

    base_time = datetime.now().replace(hour=8, minute=0)

    # Fire 3 times with 2h+ gaps
    for i in range(3):
        snap = make_snapshot(deadlines_24h=3, hour_of_day=8 + (i * 3))
        t = base_time + timedelta(hours=i * 3)
        r = engine.evaluate(snap, now=t)
        check(f"fire #{i+1}", r["triggered"] is True, f"at hour {8 + i*3}")

    # 4th should be blocked
    snap = make_snapshot(deadlines_24h=3, hour_of_day=20)
    t4 = base_time + timedelta(hours=12)
    r4 = engine.evaluate(snap, now=t4)
    check("4th blocked (daily max)", r4["triggered"] is False)

    os.unlink(tmp)


# ------------------------------------------------------------------ #
#  Test 6 — No Duplicate Firing                                        #
# ------------------------------------------------------------------ #

def test_no_duplicate():
    print("\n[Test 6] No Duplicate Firing")
    engine, tmp = fresh_engine()

    snap = make_snapshot(hour_of_day=9)
    t1 = datetime.now().replace(hour=9, minute=0)

    r1 = engine.evaluate(snap, now=t1)
    check("initial fire", r1["triggered"] is True)

    # Immediately again — should be blocked by gap
    r2 = engine.evaluate(snap, now=t1 + timedelta(minutes=5))
    check("immediate re-fire blocked", r2["triggered"] is False)

    os.unlink(tmp)


# ------------------------------------------------------------------ #
#  Runner                                                              #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    print("=" * 60)
    print("  NOVA Context Engine — Verification Suite")
    print("=" * 60)

    test_morning_trigger()
    test_deadline_pressure()
    test_discipline()
    test_cooldown()
    test_daily_max()
    test_no_duplicate()

    print("\n" + "=" * 60)
    print(f"  RESULTS: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)
