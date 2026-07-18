import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nova.apps.web.backend.main import (
    ingest_endpoint, inspect_endpoint, explore_endpoint, search_endpoint, timeline_endpoint, IngestRequest
)

def test_productization_flow():
    # 1. Ingest a test fact
    req = IngestRequest(source_type="plaintext", content="Productization test entity")
    data = ingest_endpoint(req)
    commit_hash = data["commit_hash"]
    fact_id = data["fact_id"]
    
    # 2. Test universal inspect on Commit
    insp_c = inspect_endpoint(commit_hash)
    assert insp_c["object_type"] == "Commit"
    
    # 3. Test universal inspect on Observation
    insp_o = inspect_endpoint(fact_id)
    assert insp_o["object_type"] in ("Observation", "Artifact")
    
    # 4. Test Graph Explorer Matrix
    exp = explore_endpoint()
    assert len(exp["observations"]) >= 1
    assert any(o["id"] == fact_id for o in exp["observations"])
    
    # 5. Test Deterministic Search
    matches = search_endpoint("Productization")
    assert len(matches) >= 1
    assert any("productization" in m["text"].lower() for m in matches)
    
    # 6. Test Timeline Endpoint
    timeline = timeline_endpoint()
    assert len(timeline) >= 1

if __name__ == "__main__":
    print("--- Running Productization Tests ---")
    test_productization_flow()
    print("All productization tests passed!")
