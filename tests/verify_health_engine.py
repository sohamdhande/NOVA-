#!/usr/bin/env python3
"""
verify_health_engine.py — test harness for SystemHealthEngine.

Simulates:
  1. Normal state
  2. Overdue spike
  3. Cooldown logic
  4. Smoothing precision
  5. DB persistence

Uses a temp SQLite DB so production data is never touched.
"""

import os
import sys
import tempfile
import sqlite3
from datetime import datetime, timedelta

# Resolve project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.health import HealthEngine

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    tag = "PASS" if condition else "FAIL"
    if not condition:
        FAIL += 1
    else:
        PASS += 1
    extra = f"  ({detail})" if detail else ""
    print(f"  [{tag}] {name}{extra}")


# --------------------------------------------------------------------------- #
#  Helpers                                                                     #
# --------------------------------------------------------------------------- #

def healthy_metrics():
    """All-green metrics → should yield ~100 raw."""
    return {
        "overdue_count": 0,
        "deadlines_48h": 0,
        "deadlines_24h": 0,
        "active_tasks": 5,
        "expense_logged_today": True,
        "missed_days_this_month": 0,
        "last_7_day_streak": True,
        "daemon_crash_recent": False,
        "daemon_uptime_hours": 72,
    }


def bad_metrics():
    """Stressed metrics → should drop health significantly."""
    return {
        "overdue_count": 4,
        "deadlines_48h": 2,
        "deadlines_24h": 3,
        "active_tasks": 15,
        "expense_logged_today": False,
        "missed_days_this_month": 5,
        "last_7_day_streak": False,
        "daemon_crash_recent": True,
        "daemon_uptime_hours": 0,
    }


# --------------------------------------------------------------------------- #
#  Test 1 — Normal State                                                       #
# --------------------------------------------------------------------------- #

def test_normal_state():
    print("\n[Test 1] Normal State")
    tmp = tempfile.mktemp(suffix=".db")
    engine = HealthEngine(db_path=tmp)
    result = engine.calculate_health(healthy_metrics())

    check("health is int", isinstance(result["system_health"], int))
    check("zone is stable", result["health_zone"] == "stable",
          f"got {result['health_zone']}")
    check("no trigger", result["health_trigger"] is False)
    # Raw = 100 + 3 (no deadlines) + 4 (streak) + 3 (uptime) = capped 100
    # Smoothed = round(100*0.75 + 100*0.25) = 100
    check("health == 100", result["system_health"] == 100,
          f"got {result['system_health']}")
    os.unlink(tmp)


# --------------------------------------------------------------------------- #
#  Test 2 — Overdue Spike                                                      #
# --------------------------------------------------------------------------- #

def test_overdue_spike():
    print("\n[Test 2] Overdue Spike")
    tmp = tempfile.mktemp(suffix=".db")
    engine = HealthEngine(db_path=tmp)

    # First call — healthy baseline to set prev=100
    engine.calculate_health(healthy_metrics())

    # Second call — bad metrics
    result = engine.calculate_health(bad_metrics())

    # Raw penalties:
    #   academic: 4*8=32 + 2*4=8 + 5(>12) = 45 → capped 40
    #   time: deadlines_24h>=3 → -8
    #   discipline: no expense → -6, missed>3 → -8
    #   system: crash → -10
    # total penalty = 40+8+6+8+10 = 72  →  raw = 100-72 = 28
    # Smoothed = round(100*0.75 + 28*0.25) = round(82.0) = 82
    check("health dropped", result["system_health"] < 100,
          f"got {result['system_health']}")
    check("zone not stable", result["health_zone"] != "stable",
          f"got {result['health_zone']}")
    check("trigger fired", result["health_trigger"] is True)
    os.unlink(tmp)


# --------------------------------------------------------------------------- #
#  Test 3 — Cooldown Logic                                                     #
# --------------------------------------------------------------------------- #

def test_cooldown():
    print("\n[Test 3] Cooldown Logic")
    tmp = tempfile.mktemp(suffix=".db")
    engine = HealthEngine(db_path=tmp)

    # Call 1 — baseline
    engine.calculate_health(healthy_metrics())
    # Call 2 — trigger
    r2 = engine.calculate_health(bad_metrics())
    check("first trigger fires", r2["health_trigger"] is True)

    # Call 3 — same bad metrics immediately (<30 min)
    r3 = engine.calculate_health(bad_metrics())
    check("second trigger suppressed (cooldown)", r3["health_trigger"] is False,
          "cooldown should prevent re-trigger within 30 min")
    os.unlink(tmp)


# --------------------------------------------------------------------------- #
#  Test 4 — Smoothing Precision                                                #
# --------------------------------------------------------------------------- #

def test_smoothing():
    print("\n[Test 4] Smoothing Precision")
    tmp = tempfile.mktemp(suffix=".db")
    engine = HealthEngine(db_path=tmp)

    # prev = 100 (init)
    m = healthy_metrics()
    m["overdue_count"] = 2          # academic: 16
    m["deadlines_48h"] = 1          # academic: +4 = 20  (under cap)
    m["last_7_day_streak"] = False  # no +4 bonus
    m["daemon_uptime_hours"] = 10   # no +3 bonus
    # raw = 100 - 20 + 3(no deadlines? deadlines_48h=1, so no bonus) = 100 - 20 = 80
    # Actually deadlines_48h=1 != 0, so no +3 bonus.  deadlines_24h=0, but deadlines_48h != 0
    # so the bonus condition (both==0) is NOT met → raw = 80
    # smoothed = round(100*0.75 + 80*0.25) = round(95) = 95
    result = engine.calculate_health(m)
    expected = round(100 * 0.75 + 80 * 0.25)
    check(f"smoothed == {expected}", result["system_health"] == expected,
          f"got {result['system_health']}")
    check("result is int", isinstance(result["system_health"], int))
    os.unlink(tmp)


# --------------------------------------------------------------------------- #
#  Test 5 — DB Persistence                                                     #
# --------------------------------------------------------------------------- #

def test_db_persistence():
    print("\n[Test 5] DB Persistence")
    tmp = tempfile.mktemp(suffix=".db")
    engine = HealthEngine(db_path=tmp)

    result = engine.calculate_health(healthy_metrics())
    stored_health = result["system_health"]

    # Read DB directly
    conn = sqlite3.connect(tmp)
    row = conn.execute(
        "SELECT previous_health, last_updated, last_trigger FROM system_state WHERE id = 1"
    ).fetchone()
    conn.close()

    check("row exists", row is not None)
    check("previous_health matches", row[0] == float(stored_health),
          f"db={row[0]}, returned={stored_health}")
    check("last_updated is set", row[1] is not None)
    check("last_trigger is NULL (no trigger)", row[2] is None)
    os.unlink(tmp)


# --------------------------------------------------------------------------- #
#  Runner                                                                      #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    print("=" * 60)
    print("  NOVA Health Engine — Verification Suite")
    print("=" * 60)

    test_normal_state()
    test_overdue_spike()
    test_cooldown()
    test_smoothing()
    test_db_persistence()

    print("\n" + "=" * 60)
    print(f"  RESULTS: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)
