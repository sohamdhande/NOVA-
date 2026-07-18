import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add nova to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.runtime.persistence import SQLiteCommitStore
from nova.packages.runtime.projection import project_current_state
from nova.packages.temporal.persistence import SQLiteTemporalIndex
from nova.packages.compiler import KnowledgeCommit
from nova.packages.kir import KIRNode, Dialect

def main():
    print("--- Starting Lineage Test ---")
    
    # Use memory stores for test
    store = SQLiteCommitStore(":memory:")
    temporal = SQLiteTemporalIndex(":memory:")
    
    from nova.packages.provenance.persistence import SQLiteProvenanceGraph
    from nova.packages.runtime.dependency_persistence import SQLiteDependencyGraph
    
    prov = SQLiteProvenanceGraph(":memory:")
    dep = SQLiteDependencyGraph(":memory:")
    
    import nova.packages.cli.main
    nova.packages.cli.main.get_temporal = lambda: temporal
    nova.packages.cli.main.get_provenance = lambda: prov
    nova.packages.cli.main.get_dependency = lambda: dep
    
    # Also patch integrity module's local imports
    import nova.packages.runtime.integrity
    nova.packages.runtime.integrity.get_temporal = lambda: temporal
    nova.packages.runtime.integrity.get_provenance = lambda: prov
    nova.packages.runtime.integrity.get_dependency = lambda: dep
    
    now = datetime.now(timezone.utc)
    
    # Create 4 decisions
    # A
    node_a = KIRNode(op="DECISION_MADE", inputs=[], output_id="kir_dec_A", metadata={"type": "decision", "content": "Use SQLite", "identity": "dec_A"}, dialect=Dialect.DECISION)
    # B
    node_b = KIRNode(op="DECISION_MADE", inputs=[], output_id="kir_dec_B", metadata={"type": "decision", "content": "Use Postgres", "identity": "dec_B"}, dialect=Dialect.DECISION)
    # C
    node_c = KIRNode(op="DECISION_MADE", inputs=[], output_id="kir_dec_C", metadata={"type": "decision", "content": "Use MySQL", "identity": "dec_C"}, dialect=Dialect.DECISION)
    # D (Reverts back to A)
    node_d = KIRNode(op="DECISION_MADE", inputs=[], output_id="kir_dec_D", metadata={"type": "decision", "content": "Use SQLite (Again)", "identity": "dec_D"}, dialect=Dialect.DECISION)
    
    # Commit A
    commit_1 = KnowledgeCommit(commit_hash="hash_1", kir_nodes=[node_a], parent_hash=None, created_at=now - timedelta(days=4))
    store.commit(commit_1)
    from nova.packages.temporal import TemporalRecord, TemporalInterval
    
    t_a = now - timedelta(days=4)
    record_a = TemporalRecord(
        occurrence_time=TemporalInterval(start=t_a, end=None),
        observation_time=TemporalInterval(start=t_a, end=None),
        assertion_time=TemporalInterval(start=t_a, end=None),
        compilation_time=t_a
    )
    temporal.register("dec_A", record_a)
    store.add_lineage_edge("kir_dec_A", "kir_dec_A", "SELF", t_a.isoformat()) 
    
    # Commit B supersedes A
    t_b = now - timedelta(days=3)
    commit_2 = KnowledgeCommit(commit_hash="hash_2", kir_nodes=[node_b], parent_hash="hash_1", created_at=t_b)
    store.commit(commit_2)
    record_b = TemporalRecord(
        occurrence_time=TemporalInterval(start=t_b, end=None),
        observation_time=TemporalInterval(start=t_b, end=None),
        assertion_time=TemporalInterval(start=t_b, end=None),
        compilation_time=t_b
    )
    temporal.supersede("dec_A", "dec_B", record_b, t_b)
    store.add_lineage_edge("kir_dec_A", "kir_dec_B", "SUPERSEDES", t_b.isoformat())
    
    # Commit C supersedes B
    t_c = now - timedelta(days=2)
    commit_3 = KnowledgeCommit(commit_hash="hash_3", kir_nodes=[node_c], parent_hash="hash_2", created_at=t_c)
    store.commit(commit_3)
    record_c = TemporalRecord(
        occurrence_time=TemporalInterval(start=t_c, end=None),
        observation_time=TemporalInterval(start=t_c, end=None),
        assertion_time=TemporalInterval(start=t_c, end=None),
        compilation_time=t_c
    )
    temporal.supersede("dec_B", "dec_C", record_c, t_c)
    store.add_lineage_edge("kir_dec_B", "kir_dec_C", "SUPERSEDES", t_c.isoformat())
    
    # Commit D supersedes C
    t_d = now - timedelta(days=1)
    commit_4 = KnowledgeCommit(commit_hash="hash_4", kir_nodes=[node_d], parent_hash="hash_3", created_at=t_d)
    store.commit(commit_4)
    record_d = TemporalRecord(
        occurrence_time=TemporalInterval(start=t_d, end=None),
        observation_time=TemporalInterval(start=t_d, end=None),
        assertion_time=TemporalInterval(start=t_d, end=None),
        compilation_time=t_d
    )
    temporal.supersede("dec_C", "dec_D", record_d, t_d)
    store.add_lineage_edge("kir_dec_C", "kir_dec_D", "SUPERSEDES", t_d.isoformat())
    
    # Test project_current_state
    print("\n[Test] project_current_state:")
    proj = project_current_state(store, temporal_idx=temporal)
    for f in proj.facts:
        print(f"Current Fact: {f['identity']} -> {f['content']}")
        
    # Verify ONLY dec_D is printed
    fact_ids = [f["identity"] for f in proj.facts]
    assert "dec_D" in fact_ids
    assert "dec_A" not in fact_ids
    assert "dec_B" not in fact_ids
    assert "dec_C" not in fact_ids
    print("SUCCESS: Only D is current.")
    
    # Test Lineage Endpoint logic
    print(f"\n[Test] get_lineage(kir_dec_A):")
    nodes = store.get_lineage("kir_dec_A")
    for n in nodes:
        print(f" - {n['node_id']} @ {n['occurrence_time']}")
        
    assert len(nodes) == 4
    print("SUCCESS: All 4 versions are in the lineage.")
    
    # Check Integrity snapshot volatility flag
    print("\n[Test] Volatility:")
    store._compute_integrity()
    snap = getattr(store, "integrity_snapshot", None)
    if snap:
        print("Profile keys:", snap["profiles"].keys())
        profile = snap["profiles"].get("kir_dec_D")
        if profile:
            print(f"Flags for D: {profile['integrity_flags']}")
            assert any("Volatile Lineage" in flag for flag in profile["integrity_flags"])
            print("SUCCESS: Volatility flag detected.")
        else:
            print("Profile for D not found.")
    else:
        print("No integrity snapshot.")

if __name__ == "__main__":
    main()
