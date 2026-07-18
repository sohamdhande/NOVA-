import os
import sys
import json

_nova_root = os.path.abspath(".")
if _nova_root not in sys.path:
    sys.path.insert(0, _nova_root)

from unittest.mock import patch
from nova.packages.runtime.persistence import SQLiteCommitStore
from nova.packages.runtime.state_resolution import get_state_snapshot
from api.knowledge_routes import preview_artifact, compile_artifact, PreviewRequest, CompileRequest

# Isolated DB
test_store = SQLiteCommitStore(":memory:")

mock_ai_extractions = {
    "decisions": [
        {"title": "Test Decision", "summary": "Decision Summary", "description": "Desc", "alternatives": []}
    ],
    "goals": [
        {"title": "Test Goal", "summary": "Goal Summary", "metrics": "Metrics"}
    ],
    "risks": [
        {"title": "Test Risk", "summary": "Risk Summary", "impact": "High"}
    ]
}

def mock_extract(*args, **kwargs):
    return mock_ai_extractions

def run():
    with patch("api.knowledge_routes._get_store", return_value=test_store):
        with patch("nova.packages.llm.get_provider") as get_prov:
            prov = get_prov.return_value
            prov.extract_organizational_knowledge.side_effect = mock_extract
            
            req = PreviewRequest(source_type="plaintext", content="Some content")
            preview = preview_artifact(req)
            
            for obs in preview["observations"]:
                print(f"--- OBS TYPE: {obs.get('type')} ---")
                print("raw_payload:", json.dumps(obs["raw_payload"], indent=2))
                
                # Compile it
                c_req = CompileRequest(
                    source_type="plaintext",
                    content="Some content",
                    approved_observations=[obs["raw_payload"]],
                    approved_observation_ids=[obs["id"]]
                )
                compile_artifact(c_req)
                
            snapshot = get_state_snapshot(test_store)
            print("\n=== COMPILED METADATA ===")
            for bucket_cat, bucket in snapshot.buckets.items():
                for rn in bucket:
                    print(f"[{bucket_cat}] metadata =", json.dumps(rn.node.metadata, indent=2))

if __name__ == "__main__":
    run()
