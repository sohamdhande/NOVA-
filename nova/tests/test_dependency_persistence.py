import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.runtime.dependency_persistence import SQLiteDependencyGraph

def test_dependency_persistence():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name
        
    try:
        # Instance 1
        graph1 = SQLiteDependencyGraph(db_path)
        graph1.record_dependency("proj_1", "fact_A")
        graph1.record_dependency("proj_1", "fact_B")
        graph1.record_dependency("proj_2", "fact_B")
        
        # Instance 2
        graph2 = SQLiteDependencyGraph(db_path)
        
        deps1 = graph2.get_dependencies("proj_1")
        assert len(deps1) == 2
        assert "fact_A" in deps1
        assert "fact_B" in deps1
        
        stale_projs = graph2.invalidate("fact_B")
        assert len(stale_projs) == 2
        assert "proj_1" in stale_projs
        assert "proj_2" in stale_projs
        
        stale_projs_A = graph2.invalidate("fact_A")
        assert len(stale_projs_A) == 1
        assert "proj_1" in stale_projs_A
            
    finally:
        Path(db_path).unlink()

if __name__ == "__main__":
    print("--- Testing Dependency Persistence ---")
    test_dependency_persistence()
    print("All Dependency Persistence tests passed!\n")
