import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.provenance.persistence import SQLiteProvenanceGraph
from nova.packages.provenance import ProvenanceLink, ProvenanceCycleError

def test_provenance_persistence():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = f.name
        
    try:
        # Instance 1
        graph1 = SQLiteProvenanceGraph(db_path)
        
        graph1.add_link(ProvenanceLink("A", "B", "derived_from"))
        graph1.add_link(ProvenanceLink("B", "C", "derived_from"))
        
        # Test cycle rejection
        try:
            graph1.add_link(ProvenanceLink("C", "A", "derived_from"))
            assert False, "Should have rejected cycle"
        except ProvenanceCycleError:
            pass
            
        # Instance 2
        graph2 = SQLiteProvenanceGraph(db_path)
        
        back = graph2.walk_backward("C")
        assert len(back) == 2
        assert back[0].from_fact_id == "A"
        assert back[1].to_fact_id == "C"
        
        explanation = graph2.explain("C")
        assert "A --[derived_from]--> B" in explanation
        assert "B --[derived_from]--> C" in explanation
        
        # Cycle still rejected
        try:
            graph2.add_link(ProvenanceLink("C", "A", "derived_from"))
            assert False, "Should have rejected cycle"
        except ProvenanceCycleError:
            pass
            
    finally:
        Path(db_path).unlink()

if __name__ == "__main__":
    print("--- Testing Provenance Persistence ---")
    test_provenance_persistence()
    print("All Provenance Persistence tests passed!\n")
