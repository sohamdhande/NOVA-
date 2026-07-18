import pytest
import json
from datetime import datetime, timezone
from nova.packages.compiler import KnowledgeCommit
from nova.packages.kir import KIRNode, Dialect
from nova.packages.runtime.store import KnowledgeStore
from nova.packages.runtime.integrity import compute_integrity_snapshot

@pytest.fixture
def store():
    return KnowledgeStore()

def test_integrity_snapshot(store):
    node1 = KIRNode(
        op="ASSERT",
        inputs=[],
        output_id="dec_1",
        metadata={
            "type": "DECISION",
            "content": {
                "decision": "Use PostgreSQL",
                "status": "active"
            },
            "confidence": 0.9,
            "source_path": "/docs/arch.md"
        },
        dialect=Dialect.GENERIC
    )
    
    node2 = KIRNode(
        op="ASSERT",
        inputs=[],
        output_id="goal_1",
        metadata={
            "type": "GOAL",
            "content": {
                "goal": "Improve latency",
                "status": "active"
            },
            "confidence": 0.8
        },
        dialect=Dialect.GENERIC
    )
    
    # Action item linked to decision but not goal
    node3 = KIRNode(
        op="ASSERT",
        inputs=[],
        output_id="action_1",
        metadata={
            "type": "ACTION_ITEM",
            "content": {
                "action": "Setup DB",
                "related_decision": "dec_1"
            },
            "confidence": 0.9
        },
        dialect=Dialect.GENERIC
    )
    
    commit1 = KnowledgeCommit(
        commit_hash="hash1",
        parent_hash=None,
        kir_nodes=[node1, node2, node3],
        created_at=datetime.now(timezone.utc)
    )
    store._history.append(commit1)
    
    snap = compute_integrity_snapshot(store)
    
    assert snap["health_score"] > 0
    assert "dec_1" in snap["profiles"]
    assert "goal_1" in snap["profiles"]
    
    # dec_1 should NOT be lonely because it has an action item
    dec_profile = snap["profiles"]["dec_1"]
    assert not any("Lonely Knowledge" in f for f in dec_profile["integrity_flags"])
    
    # goal_1 SHOULD be lonely because it has no action item
    goal_profile = snap["profiles"]["goal_1"]
    assert any("Lonely Knowledge" in f for f in goal_profile["integrity_flags"])
    
    assert len(snap["lonely_knowledge"]) == 1
    assert snap["lonely_knowledge"][0]["id"] == "goal_1"

def test_contradiction_detection(store):
    rel_node = KIRNode(
        op="RELATE",
        inputs=[],
        output_id="rel_1",
        metadata={
            "type": "RELATIONSHIP",
            "content": {
                "source": "princ_1",
                "target": "dec_2",
                "relation": "CONTRADICTS"
            },
            "confidence": 0.9,
            "source_path": "/docs/review.md"
        },
        dialect=Dialect.GENERIC
    )
    
    princ_node = KIRNode(
        op="ASSERT",
        inputs=[],
        output_id="princ_1",
        metadata={"type": "PRINCIPLE", "content": {}, "confidence": 0.9},
        dialect=Dialect.GENERIC
    )
    
    dec_node = KIRNode(
        op="ASSERT",
        inputs=[],
        output_id="dec_2",
        metadata={"type": "DECISION", "content": {}, "confidence": 0.8},
        dialect=Dialect.GENERIC
    )
    
    commit = KnowledgeCommit(
        commit_hash="hash2",
        parent_hash=None,
        kir_nodes=[princ_node, dec_node, rel_node],
        created_at=datetime.now(timezone.utc)
    )
    store._history.append(commit)
    
    snap = compute_integrity_snapshot(store)
    
    assert len(snap["contradictions"]) == 1
    c = snap["contradictions"][0]
    assert c["type"] == "Principle conflicts with Decision"
    assert "princ_1" in c["objects_involved"]
    assert "dec_2" in c["objects_involved"]
