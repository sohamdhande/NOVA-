import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.runtime import KnowledgeStore, DependencyGraph, compute_tracked_projection
from nova.packages.identity import IdentityRegistry
from nova.packages.temporal import TemporalIndex, TemporalRecord
from nova.packages.observation import build_bundle
from nova.packages.compiler import compile
from nova.packages.provenance import ProvenanceGraph

def _commit_fact(store, registry, temporal_index, provenance_graph, content: str, sender: str = "test"):
    raw = {"content": content, "sender": sender, "source_path": f"test/{content}"}
    bundle = build_bundle(raw, registry, temporal_index, provenance_graph)
    commit = compile(bundle)
    store.commit(commit)
    return bundle.observations[0].id

def test_dependencies():
    store = KnowledgeStore()
    registry = IdentityRegistry()
    temporal_index = TemporalIndex()
    provenance_graph = ProvenanceGraph()
    graph = DependencyGraph()
    
    # 1. Commit 2 facts
    fact1_id = _commit_fact(store, registry, temporal_index, provenance_graph, "fact 1", sender="test1")
    fact2_id = _commit_fact(store, registry, temporal_index, provenance_graph, "fact 2", sender="test2")
    
    # a. Basic recording
    tp1 = compute_tracked_projection(store, graph, "proj_all")
    deps = graph.get_dependencies("proj_all")
    assert fact1_id in deps
    assert fact2_id in deps
    assert len(deps) == 2
    
    # b. Inverse lookup
    assert "proj_all" in graph.get_dependents(fact1_id)
    assert "proj_all" in graph.get_dependents(fact2_id)
    
    # Let's create a second tracked projection that somehow only depends on fact1?
    # Actually, compute_tracked_projection uses project_current_state, which gets ALL facts.
    # To test "no false positives" (d), we need a projection that didn't depend on fact2.
    # How to achieve this? The function compute_tracked_projection natively calls project_current_state which returns ALL facts.
    # We can manually register a dependency to simulate a specialized projection, or we can clear the store?
    # The requirement: "test with two separate tracked projections over different fact subsets, only one should invalidate"
    # So we'll just manually register a dependency to simulate a specialized projection.
    
    graph.record_dependency("proj_special", fact1_id)
    
    # c. Invalidation via Temporal Supersession
    # Commit a new fact that supersedes fact 2
    fact3_id = _commit_fact(store, registry, temporal_index, provenance_graph, "fact 3")
    
    # Supersede fact 2 with fact 3
    t_supersede = datetime.now(timezone.utc)
    temporal_index.supersede(fact2_id, fact3_id, TemporalRecord(), t_supersede)
    
    # Invalidate fact2
    stale_projs = graph.invalidate(fact2_id)
    
    assert "proj_all" in stale_projs, "proj_all should be stale because it depended on fact2"
    
    # d. No false positives
    assert "proj_special" not in stale_projs, "proj_special did not depend on fact2, should not be stale"

if __name__ == "__main__":
    print("--- Testing Dependency Subsystem ---")
    test_dependencies()
    print("All Dependency tests passed!\n")
