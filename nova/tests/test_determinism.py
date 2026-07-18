import sys
from pathlib import Path
import copy

# Add project root to sys.path to resolve 'nova'
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.observation import build_bundle
from nova.packages.compiler import compile

from nova.packages.identity import IdentityRegistry
from nova.packages.temporal import TemporalIndex
from nova.packages.provenance import ProvenanceGraph

def test_determinism():
    registry = IdentityRegistry()
    temporal_index = TemporalIndex()
    provenance_graph = ProvenanceGraph()
    
    raw_artifact_1 = {
        "source_path": "slack/general/msg_1042",
        "sender": "Alice",
        "content": "The knowledge compilation platform architecture is frozen."
    }
    
    raw_artifact_2 = copy.deepcopy(raw_artifact_1)
    
    bundle_1 = build_bundle(raw_artifact_1, registry, temporal_index, provenance_graph)
    commit_1 = compile(bundle_1)
    
    bundle_2 = build_bundle(raw_artifact_2, registry, temporal_index, provenance_graph)
    commit_2 = compile(bundle_2)
    
    print(f"Commit 1 hash: {commit_1.commit_hash}")
    print(f"Commit 2 hash: {commit_2.commit_hash}")
    
    assert commit_1.commit_hash == commit_2.commit_hash
    print("Determinism test passed: Same input yielded IDENTICAL commit hash.")

def test_determinism_regression_ignores_state():
    from nova.packages.provenance import ProvenanceLink
    registry = IdentityRegistry()
    
    raw = {"source_path": "x", "sender": "test", "content": "hello"}
    
    # 1. Base compile
    t_idx_1 = TemporalIndex()
    p_graph_1 = ProvenanceGraph()
    b1 = build_bundle(raw, registry, t_idx_1, p_graph_1)
    c1 = compile(b1)
    
    # 2. Compile with different temporal state and provenance
    t_idx_2 = TemporalIndex()
    p_graph_2 = ProvenanceGraph()
    # Add some dummy link
    p_graph_2.add_link(ProvenanceLink("some_parent", "dummy", "test_rel"))
    
    import time
    time.sleep(0.1)
    
    b2 = build_bundle(raw, registry, t_idx_2, p_graph_2, derived_from_ids=[("some_parent", "test_rel")])
    c2 = compile(b2)
    
    assert c1.commit_hash == c2.commit_hash
    print("Regression passed: Commit hash ignores temporal intervals and provenance graph.")

if __name__ == "__main__":
    test_determinism()
    test_determinism_regression_ignores_state()
