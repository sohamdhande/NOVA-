import sys
from pathlib import Path

# Add project root to sys.path to resolve 'nova'
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.observation import build_bundle
from nova.packages.compiler import compile, KnowledgeCommit
from nova.packages.runtime import KnowledgeStore, project_current_state, ChainIntegrityError

from nova.packages.identity import IdentityRegistry
from nova.packages.temporal import TemporalIndex
from nova.packages.provenance import ProvenanceGraph

def test_runtime_chaining_and_projections():
    store = KnowledgeStore()
    registry = IdentityRegistry()
    temporal_index = TemporalIndex()
    provenance_graph = ProvenanceGraph()
    
    events = []
    def on_commit(kc: KnowledgeCommit):
        events.append(kc.commit_hash)
    store.subscribe(on_commit)
    
    # Commit 1
    raw1 = {"source_path": "file_1.txt", "content": "Initial", "sender": "test1"}
    bundle1 = build_bundle(raw1, registry, temporal_index, provenance_graph)
    commit1 = compile(bundle1)
    store.commit(commit1)
    
    # Commit 2
    raw2 = {"source_path": "file_2.txt", "content": "Follow up", "sender": "test2"}
    bundle2 = build_bundle(raw2, registry, temporal_index, provenance_graph)
    commit2 = compile(bundle2)
    store.commit(commit2)
    
    chain = store.get_chain()
    assert len(chain) == 2
    assert chain[0].parent_hash is None
    assert chain[1].parent_hash == chain[0].commit_hash
    
    # Check Projection
    proj = project_current_state(store)
    assert len(proj.facts) == 2, f"Expected 2 facts, got {len(proj.facts)}"
    
    # Check Subscriptions
    assert len(events) == 2, "Expected 2 subscription events"
    assert events[0] == commit1.commit_hash
    assert events[1] == commit2.commit_hash
    
    print("Runtime chaining, projections, and subscriptions test passed.")

if __name__ == "__main__":
    print("--- Testing Runtime ---")
    test_runtime_chaining_and_projections()
    print("All Runtime tests passed!\n")
