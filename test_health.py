import sys
import os

# Add parent directory to path
sys.path.append(os.getcwd())

from core.health import HealthEngine

def test_health():
    print("Initializing HealthEngine...")
    engine = HealthEngine()
    
    metrics = {
        "overdue_count": 0,
        "deadlines_48h": 0,
        "active_tasks": 5,
        "expenses_missing_today": False,
        "missing_expense_days_count": 0,
        "daemon_running": True
    }
    
    print("Calculating Health (Run 1)...")
    result = engine.calculate_health(metrics)
    print("Result:", result)
    
    # Run 2 with bad metrics to see change
    bad_metrics = {
        "overdue_count": 2,
        "deadlines_48h": 1,
        "active_tasks": 15,
        "expenses_missing_today": True,
        "missing_expense_days_count": 5,
        "daemon_running": False
    }
    
    print("\nCalculating Health (Run 2 - Bad Metrics)...")
    result2 = engine.calculate_health(bad_metrics)
    print("Result:", result2)
    
    print("\nTest Complete.")

if __name__ == "__main__":
    test_health()
