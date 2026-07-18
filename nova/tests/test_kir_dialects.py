import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.ontology import SemanticType
from nova.packages.kir import Dialect, classify_dialect, lower_to_kir, KIRNode
from nova.packages.observation import Observation
from nova.packages.temporal import TemporalRecord
from nova.packages.provenance import ProvenanceChain
from nova.packages.compiler import compute_commit_hash

def _mock_obs(content: dict, type_val: SemanticType = SemanticType.ARTIFACT) -> Observation:
    return Observation(
        id="test_obs",
        type=type_val,
        content=content,
        identity="test_id",
        temporal=TemporalRecord(),
        provenance=ProvenanceChain("test", [])
    )

def test_classify_dialect():
    obs_slack = _mock_obs({"channel": "general", "text": "Hello"})
    assert classify_dialect(obs_slack) == Dialect.COMMUNICATION
    
    obs_git = _mock_obs({"commit": "abc1234", "message": "Fix bug"})
    assert classify_dialect(obs_git) == Dialect.CODE_CHANGE
    
    obs_dec = _mock_obs({"text": "We will use Python"}, type_val=SemanticType.DECISION)
    assert classify_dialect(obs_dec) == Dialect.DECISION
    
    obs_gen = _mock_obs({"random_key": "val"})
    assert classify_dialect(obs_gen) == Dialect.GENERIC

def test_lower_to_kir_ops():
    # COMMUNICATION -> MESSAGE_SENT
    n1 = lower_to_kir(_mock_obs({"channel": "general", "text": "Hello"}))
    assert n1.dialect == Dialect.COMMUNICATION
    assert n1.op == "MESSAGE_SENT"
    
    # COMMUNICATION -> THREAD_REPLY
    n2 = lower_to_kir(_mock_obs({"channel": "general", "text": "Reply", "thread_ts": "123"}))
    assert n2.dialect == Dialect.COMMUNICATION
    assert n2.op == "THREAD_REPLY"
    
    # CODE_CHANGE -> COMMIT
    n3 = lower_to_kir(_mock_obs({"commit": "abc", "message": "msg"}))
    assert n3.dialect == Dialect.CODE_CHANGE
    assert n3.op == "COMMIT"
    
    # CODE_CHANGE -> DIFF_APPLIED
    n4 = lower_to_kir(_mock_obs({"sha": "abc", "diff": "+++"}))
    assert n4.dialect == Dialect.CODE_CHANGE
    assert n4.op == "DIFF_APPLIED"
    
    # DECISION -> DECISION_MADE
    n5 = lower_to_kir(_mock_obs({"some": "val"}, type_val=SemanticType.DECISION))
    assert n5.dialect == Dialect.DECISION
    assert n5.op == "DECISION_MADE"
    
    # GENERIC -> OBSERVE
    n6 = lower_to_kir(_mock_obs({"unknown": "val"}))
    assert n6.dialect == Dialect.GENERIC
    assert n6.op == "OBSERVE"

def test_determinism():
    obs = _mock_obs({"channel": "general", "text": "Hello"})
    n1 = lower_to_kir(obs)
    n2 = lower_to_kir(obs)
    assert n1 == n2
    
def test_hash_sensitivity():
    # Two nodes with identical everything except dialect
    n1 = KIRNode(
        op="OBSERVE",
        inputs=[],
        output_id="node1",
        metadata={"key": "val"},
        dialect=Dialect.COMMUNICATION
    )
    
    n2 = KIRNode(
        op="OBSERVE",
        inputs=[],
        output_id="node1",
        metadata={"key": "val"},
        dialect=Dialect.CODE_CHANGE
    )
    
    h1 = compute_commit_hash([n1])
    h2 = compute_commit_hash([n2])
    
    assert h1 != h2, "Dialect must affect hash determinism!"
    
if __name__ == "__main__":
    print("--- Testing KIR Dialects Subsystem ---")
    test_classify_dialect()
    test_lower_to_kir_ops()
    test_determinism()
    test_hash_sensitivity()
    print("All KIR Dialects tests passed!\n")
