import pytest
from api.knowledge_routes import preview_artifact, compile_artifact, _get_store, PreviewRequest, CompileRequest
from nova.packages.runtime.state_resolution import get_state_snapshot
from nova.packages.ontology import SemanticType
from unittest.mock import patch

from nova.packages.runtime.persistence import SQLiteCommitStore

# Mock the store for the test
_test_store = SQLiteCommitStore(":memory:")

@pytest.fixture(autouse=True)
def isolated_store():
    with patch("api.knowledge_routes._get_store", return_value=_test_store):
        yield

def test_preview_to_compile_pipeline_type_preservation(isolated_store):
    mock_ai_extraction = {
        "decisions": [
            {
                "title": "Adopt SemanticType for all nodes",
                "summary": "We will use the 'type' field rather than 'semantic_type' going forward."
            }
        ]
    }
    
    with patch("nova.packages.llm.get_provider") as mock_get_provider:
        mock_provider = mock_get_provider.return_value
        mock_provider.extract_organizational_knowledge.return_value = mock_ai_extraction
        
        # 1. Preview
        req_preview = PreviewRequest(
            source_type="plaintext",
            content="We decided to adopt SemanticType for all nodes to fix the type mismatch.",
            title="Type Mismatch Decision"
        )
        preview_data = preview_artifact(req_preview)
        
        # Verify preview gave us the decision
        decisions = [o for o in preview_data["observations"] if o["type"] == "DECISION"]
        assert len(decisions) == 1
        
        decision = decisions[0]
        payload_to_compile = decision["raw_payload"]
        
        # 2. Compile
        req_compile = CompileRequest(
            source_type="plaintext",
            content="We decided to adopt SemanticType for all nodes to fix the type mismatch.",
            title="Type Mismatch Decision",
            approved_observations=[payload_to_compile],
            approved_observation_ids=[decision["id"]]
        )
        compile_res = compile_artifact(req_compile)
        
        assert compile_res["status"] == "success"
        
        # 3. Verify it was correctly bucketed by bucket_by_category()
        store = _get_store()
        snapshot = get_state_snapshot(store)
        
        assert "DECISION" in snapshot.category_counts
        assert snapshot.category_counts["DECISION"] == 1
        
        dec_bucket = snapshot.buckets["DECISION"]
        assert len(dec_bucket) == 1
        
        assert dec_bucket[0].node.metadata["type"] == "DECISION"
        assert dec_bucket[0].node.metadata["content"]["title"] == "Adopt SemanticType for all nodes"

