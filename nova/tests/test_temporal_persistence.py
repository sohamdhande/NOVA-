import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.temporal.persistence import SQLiteTemporalIndex
from nova.packages.temporal import TemporalRecord, TemporalInterval

def test_temporal_persistence():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name
        
    try:
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 2, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 3, tzinfo=timezone.utc)
        
        # Instance 1
        idx1 = SQLiteTemporalIndex(db_path)
        
        rec1 = TemporalRecord(assertion_time=TemporalInterval(start=t0))
        idx1.register("rock", rec1)
        
        rec2 = TemporalRecord(assertion_time=TemporalInterval(start=t2))
        idx1.supersede("rock", "cheese", rec2, at_time=t2)
        
        # Instance 2
        idx2 = SQLiteTemporalIndex(db_path)
        
        # Before supersession -> only rock
        assert set(idx2.valid_facts_as_of(t1)) == {"rock"}
        
        # After supersession -> only cheese
        assert set(idx2.valid_facts_as_of(t2)) == {"cheese"}
        
    finally:
        Path(db_path).unlink()

if __name__ == "__main__":
    print("--- Testing Temporal Persistence ---")
    test_temporal_persistence()
    print("All Temporal Persistence tests passed!\n")
