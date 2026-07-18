import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nova.packages.provenance import ProvenanceGraph, ProvenanceLink, ProvenanceCycleError

def test_multi_hop_backward():
    graph = ProvenanceGraph()
    # Decision -> Meeting -> Slack Thread -> Git Commit -> Deployment -> Outcome
    graph.add_link(ProvenanceLink("Decision", "Meeting", "produced"))
    graph.add_link(ProvenanceLink("Meeting", "Slack_Thread", "discussed_in"))
    graph.add_link(ProvenanceLink("Slack_Thread", "Git_Commit", "informed_by"))
    graph.add_link(ProvenanceLink("Git_Commit", "Deployment", "implements"))
    graph.add_link(ProvenanceLink("Deployment", "Outcome", "resulted_in"))
    
    backward = graph.walk_backward("Outcome")
    
    assert len(backward) == 5
    assert backward[0].from_fact_id == "Decision"
    assert backward[1].from_fact_id == "Meeting"
    assert backward[2].from_fact_id == "Slack_Thread"
    assert backward[3].from_fact_id == "Git_Commit"
    assert backward[4].from_fact_id == "Deployment"
    
def test_multiple_parents():
    graph = ProvenanceGraph()
    # Decision -> Meeting, Risk -> Meeting
    graph.add_link(ProvenanceLink("Decision", "Meeting", "produced"))
    graph.add_link(ProvenanceLink("Risk", "Meeting", "informed_by"))
    
    backward = graph.walk_backward("Meeting")
    assert len(backward) == 2
    from_ids = [link.from_fact_id for link in backward]
    assert "Decision" in from_ids
    assert "Risk" in from_ids
    
def test_cycle_rejection():
    graph = ProvenanceGraph()
    graph.add_link(ProvenanceLink("A", "B", "rel1"))
    graph.add_link(ProvenanceLink("B", "C", "rel2"))
    
    try:
        graph.add_link(ProvenanceLink("C", "A", "rel3"))
        assert False, "Should have raised ProvenanceCycleError"
    except ProvenanceCycleError:
        pass
        
    backward = graph.walk_backward("C")
    assert len(backward) == 2 # Only A->B and B->C, the rejected one is not there
    assert "A" in [l.from_fact_id for l in backward]

def test_forward_walk():
    graph = ProvenanceGraph()
    graph.add_link(ProvenanceLink("Decision", "Meeting", "produced"))
    graph.add_link(ProvenanceLink("Meeting", "Slack_Thread", "discussed_in"))
    
    forward = graph.walk_forward("Decision")
    assert len(forward) == 2
    assert forward[0].to_fact_id == "Meeting"
    assert forward[1].to_fact_id == "Slack_Thread"
    
def test_explain_output():
    graph = ProvenanceGraph()
    graph.add_link(ProvenanceLink("Decision", "Meeting", "produced"))
    graph.add_link(ProvenanceLink("Meeting", "Slack_Thread", "discussed_in"))
    
    explanation = graph.explain("Slack_Thread")
    assert "Decision --[produced]--> Meeting" in explanation
    assert "Meeting --[discussed_in]--> Slack_Thread" in explanation

if __name__ == "__main__":
    print("--- Testing Provenance Subsystem ---")
    test_multi_hop_backward()
    test_multiple_parents()
    test_cycle_rejection()
    test_forward_walk()
    test_explain_output()
    print("All Provenance tests passed!\n")
