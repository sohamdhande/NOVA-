import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add nova to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.runtime.persistence import SQLiteCommitStore
from nova.packages.compiler import KnowledgeCommit
from nova.packages.kir import KIRNode, Dialect
from nova.packages.runtime.state_resolution import resolve_current_state, ResolvedNode, bucket_by_category, get_state_snapshot, get_alternatives_for_decision, find_ambiguous_alternative_links, AlternativeMatch

def test_resolve_current_state():
    print("--- Starting State Resolution Tests ---")
    store = SQLiteCommitStore(":memory:")
    
    now = datetime.now(timezone.utc)
    
    # Create 3 nodes for testing
    node_a = KIRNode(op="DECISION", inputs=[], output_id="kir_A", metadata={"type": "decision"}, dialect=Dialect.GENERIC)
    node_b = KIRNode(op="DECISION", inputs=[], output_id="kir_B", metadata={"type": "decision"}, dialect=Dialect.GENERIC)
    node_c = KIRNode(op="DECISION", inputs=[], output_id="kir_C", metadata={"type": "decision"}, dialect=Dialect.GENERIC)
    node_d = KIRNode(op="DECISION", inputs=[], output_id="kir_D", metadata={"type": "decision"}, dialect=Dialect.GENERIC)
    
    # 1. Commit Node A (No edges)
    t_a = now - timedelta(days=4)
    commit_1 = KnowledgeCommit(commit_hash="hash_1", kir_nodes=[node_a], parent_hash=None, created_at=t_a)
    store.commit(commit_1)
    
    # 2. Commit Node B and C (B will be superseded by C, C will be invalidated by D)
    t_b = now - timedelta(days=3)
    commit_2 = KnowledgeCommit(commit_hash="hash_2", kir_nodes=[node_b, node_c], parent_hash="hash_1", created_at=t_b)
    store.commit(commit_2)
    
    # Node C supersedes Node B
    t_c_edge = (now - timedelta(days=2)).isoformat()
    store.add_lineage_edge("kir_B", "kir_C", "SUPERSEDES", t_c_edge)
    
    # 3. Commit Node D (D invalidates C)
    t_d = now - timedelta(days=1)
    commit_3 = KnowledgeCommit(commit_hash="hash_3", kir_nodes=[node_d], parent_hash="hash_2", created_at=t_d)
    store.commit(commit_3)
    
    # Node D invalidates Node C
    t_d_edge = now.isoformat()
    store.add_lineage_edge("kir_C", "kir_D", "INVALIDATES", t_d_edge)
    
    # Resolve State
    resolved = resolve_current_state(store)
    
    # Asserts
    
    # A node with no lineage edges resolves to ACTIVE.
    assert "kir_A" in resolved, "kir_A should be in resolved map"
    assert resolved["kir_A"].status == "ACTIVE", f"Expected ACTIVE, got {resolved['kir_A'].status}"
    assert resolved["kir_A"].superseded_by is None, "Active node should not have a superseded_by value"
    
    # A node with an outgoing SUPERSEDES edge resolves to SUPERSEDED with the correct superseded_by id.
    assert "kir_B" in resolved, "kir_B should be in resolved map"
    assert resolved["kir_B"].status == "SUPERSEDED", f"Expected SUPERSEDED, got {resolved['kir_B'].status}"
    assert resolved["kir_B"].superseded_by == "kir_C", f"Expected kir_C, got {resolved['kir_B'].superseded_by}"
    
    # A node with an outgoing INVALIDATES edge resolves to INVALIDATED.
    assert "kir_C" in resolved, "kir_C should be in resolved map"
    assert resolved["kir_C"].status == "INVALIDATED", f"Expected INVALIDATED, got {resolved['kir_C'].status}"
    assert resolved["kir_C"].superseded_by == "kir_D", f"Expected kir_D, got {resolved['kir_C'].superseded_by}"
    
    # Node D should be ACTIVE
    assert "kir_D" in resolved, "kir_D should be in resolved map"
    assert resolved["kir_D"].status == "ACTIVE", f"Expected ACTIVE, got {resolved['kir_D'].status}"
    
    print("SUCCESS: All state resolution tests passed.")

def test_bucket_by_category():
    print("--- Starting Category Bucketing Tests ---")
    store = SQLiteCommitStore(":memory:")
    now = datetime.now(timezone.utc)
    
    # Create nodes with different categories
    node_dec = KIRNode(op="DECISION", inputs=[], output_id="kir_dec", metadata={"type": "DECISION"}, dialect=Dialect.GENERIC)
    node_goal = KIRNode(op="GOAL", inputs=[], output_id="kir_goal", metadata={"type": "GOAL"}, dialect=Dialect.GENERIC)
    
    # Create node with missing type
    node_missing = KIRNode(op="OBSERVATION", inputs=[], output_id="kir_miss", metadata={"content": "no type"}, dialect=Dialect.GENERIC)
    
    # Create node with non-string type
    node_bad = KIRNode(op="OBSERVATION", inputs=[], output_id="kir_bad", metadata={"type": 123}, dialect=Dialect.GENERIC)
    
    # Commit all
    commit = KnowledgeCommit(commit_hash="hash_b1", kir_nodes=[node_dec, node_goal, node_missing, node_bad], parent_hash=None, created_at=now)
    store.commit(commit)
    
    resolved = resolve_current_state(store)
    buckets = bucket_by_category(resolved)
    
    # Asserts
    # Nodes of two different categories get correctly separated into their own buckets.
    assert "DECISION" in buckets, "DECISION bucket missing"
    assert len(buckets["DECISION"]) == 1
    assert buckets["DECISION"][0].node.output_id == "kir_dec"
    
    assert "GOAL" in buckets, "GOAL bucket missing"
    assert len(buckets["GOAL"]) == 1
    assert buckets["GOAL"][0].node.output_id == "kir_goal"
    
    # A node with a missing/unrecognized metadata["type"] lands in "uncategorized" rather than being dropped.
    assert "uncategorized" in buckets, "uncategorized bucket missing"
    assert len(buckets["uncategorized"]) == 2
    uncategorized_ids = [r.node.output_id for r in buckets["uncategorized"]]
    assert "kir_miss" in uncategorized_ids
    assert "kir_bad" in uncategorized_ids
    
    print("SUCCESS: All category bucketing tests passed.")

def test_snapshot_and_alternatives():
    print("--- Starting Snapshot & Alternatives Tests ---")
    import json
    store = SQLiteCommitStore(":memory:")
    now = datetime.now(timezone.utc)
    
    # 1. Decision 1: "Adopt PostgreSQL" (Exact match target)
    dec1 = KIRNode(op="DECISION", inputs=[], output_id="kir_dec1", 
                   metadata={"type": "DECISION", "content": json.dumps({"title": "Adopt PostgreSQL"})}, 
                   dialect=Dialect.GENERIC)
                   
    # 2. Decision 2: "Migrate to PostgreSQL for better performance" (Partial match target)
    dec2 = KIRNode(op="DECISION", inputs=[], output_id="kir_dec2", 
                   metadata={"type": "DECISION", "content": json.dumps({"title": "Migrate to PostgreSQL for better performance"})}, 
                   dialect=Dialect.GENERIC)
                   
    # 3. Decision 3: "Use SQLite for cache"
    dec3 = KIRNode(op="DECISION", inputs=[], output_id="kir_dec3", 
                   metadata={"type": "DECISION", "content": json.dumps({"title": "Use SQLite for cache"})}, 
                   dialect=Dialect.GENERIC)
                   
    # Alt 1: Exact match for Decision 1
    alt1 = KIRNode(op="ALTERNATIVE", inputs=[], output_id="kir_alt1", 
                   metadata={"type": "ALTERNATIVE", "content": json.dumps({"chosen_option": "Adopt PostgreSQL"})}, 
                   dialect=Dialect.GENERIC)
                   
    # Alt 2: Partial match for Decision 2 (only matches dec2)
    alt2 = KIRNode(op="ALTERNATIVE", inputs=[], output_id="kir_alt2", 
                   metadata={"type": "ALTERNATIVE", "content": json.dumps({"chosen_option": "Migrate to PostgreSQL"})}, 
                   dialect=Dialect.GENERIC)
                   
    # Alt 3: Ambiguous match (matches dec1, dec2, and another decision? Wait, chosen="PostgreSQL" matches both dec1 and dec2)
    alt3 = KIRNode(op="ALTERNATIVE", inputs=[], output_id="kir_alt3", 
                   metadata={"type": "ALTERNATIVE", "content": json.dumps({"chosen_option": "PostgreSQL"})}, 
                   dialect=Dialect.GENERIC)
                        
    # Commit all
    commit = KnowledgeCommit(commit_hash="hash_snap1", kir_nodes=[dec1, dec2, dec3, alt1, alt2, alt3], parent_hash=None, created_at=now)
    store.commit(commit)
    
    snapshot = get_state_snapshot(store)
    
    # Test Exact Match
    linked1 = get_alternatives_for_decision(snapshot, "kir_dec1")
    # alt1 matches exact, alt3 matches ambiguously
    assert len(linked1) == 2
    for m in linked1:
        if m.alternative.node.output_id == "kir_alt1":
            assert m.match_confidence == "exact"
            assert m.matched_on == "adopt postgresql"
        elif m.alternative.node.output_id == "kir_alt3":
            assert m.match_confidence == "ambiguous"
            
    # Test Partial Match
    linked2 = get_alternatives_for_decision(snapshot, "kir_dec2")
    # alt2 matches partial, alt3 matches ambiguously
    assert len(linked2) == 2
    for m in linked2:
        if m.alternative.node.output_id == "kir_alt2":
            assert m.match_confidence == "partial"
        elif m.alternative.node.output_id == "kir_alt3":
            assert m.match_confidence == "ambiguous"
            
    # Test Ambiguous Links function
    ambiguous_links = find_ambiguous_alternative_links(store)
    assert len(ambiguous_links) == 1
    assert ambiguous_links[0].alternative.node.output_id == "kir_alt3"
    assert ambiguous_links[0].match_confidence == "ambiguous"
    
    print("SUCCESS: All Snapshot & Alternatives tests passed.")

if __name__ == "__main__":
    test_resolve_current_state()
    test_bucket_by_category()
    test_snapshot_and_alternatives()
