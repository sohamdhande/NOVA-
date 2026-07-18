import sys
from pathlib import Path

# Add project root to sys.path to resolve 'nova'
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.observation import build_bundle
from nova.packages.compiler import compile
from nova.packages.runtime import KnowledgeStore
from nova.packages.reasoning import (
    compile_reasoning_context, 
    verify_reasoning_ir, 
    ReasoningIR, 
    ReasoningPlan, 
    ReasoningVerificationError
)

from nova.packages.identity import IdentityRegistry
from nova.packages.temporal import TemporalIndex
from nova.packages.provenance import ProvenanceGraph

def test_reasoning_slack_match():
    store = KnowledgeStore()
    registry = IdentityRegistry()
    temporal_index = TemporalIndex()
    provenance_graph = ProvenanceGraph()
    
    # Slack fact
    bundle1 = build_bundle({"source": "slack", "content": "Slack architectural goals.", "sender": "test1"}, registry, temporal_index, provenance_graph)
    commit1 = compile(bundle1)
    store.commit(commit1)
    
    # Git fact
    bundle2 = build_bundle({"source": "git", "content": "Database migrations.", "sender": "test2"}, registry, temporal_index, provenance_graph)
    commit2 = compile(bundle2)
    store.commit(commit2)
    
    intent = "What is the core architectural goal mentioned in slack?"
    context = compile_reasoning_context(intent, store)
    
    assert "slack" in context.lower()
    assert "database migrations" not in context.lower()
    print("Test passed: 'slack' intent correctly filtered facts.")

def test_reasoning_fallback():
    store = KnowledgeStore()
    registry = IdentityRegistry()
    temporal_index = TemporalIndex()
    provenance_graph = ProvenanceGraph()
    
    bundle1 = build_bundle({"content": "Some fact.", "sender": "test1"}, registry, temporal_index, provenance_graph)
    commit1 = compile(bundle1)
    store.commit(commit1)
    
    # Intent matches nothing
    intent = "database migration"
    context = compile_reasoning_context(intent, store)
    
    assert "some fact" in context.lower()
    print("Test passed: fallback behavior included all facts when no keywords matched.")

def test_verify_reasoning_ir():
    plan = ReasoningPlan(intent="test", keywords=["test"])
    empty_rir = ReasoningIR(selected_facts=[], plan=plan)
    
    try:
        verify_reasoning_ir(empty_rir)
        assert False, "Should have raised ReasoningVerificationError on empty facts"
    except ReasoningVerificationError as e:
        print(f"Test passed: verification caught empty selected_facts. ({e})")

if __name__ == "__main__":
    print("--- Testing Reasoning Compiler ---")
    test_reasoning_slack_match()
    test_reasoning_fallback()
    test_verify_reasoning_ir()
    print("All Reasoning Compiler tests passed!\n")
