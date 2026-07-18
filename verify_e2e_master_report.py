import os
import sys
import json

_nova_root = os.path.abspath(".")
if _nova_root not in sys.path:
    sys.path.insert(0, _nova_root)

from unittest.mock import patch
from nova.packages.runtime.persistence import SQLiteCommitStore
from nova.packages.runtime.state_resolution import get_state_snapshot
from nova.packages.runtime.master_report import update_and_render_master_report
from api.knowledge_routes import preview_artifact, compile_artifact, PreviewRequest, CompileRequest

# Isolated DB
test_store = SQLiteCommitStore(":memory:")

mock_ai_extractions = {
    "decisions": [
        {"title": "Test Decision", "summary": "Decision Summary", "description": "Desc", "alternatives": []}
    ],
    "goals": [
        {"title": "Test Goal", "summary": "Goal Summary", "description": "Goal Description", "metrics": "Metrics"}
    ],
    "risks": [
        {"title": "Test Risk", "summary": "Risk Summary", "description": "Risk Description", "impact": "High"}
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
                # Compile it
                c_req = CompileRequest(
                    source_type="plaintext",
                    content="Some content",
                    approved_observations=[obs["raw_payload"]],
                    approved_observation_ids=[obs["id"]]
                )
                compile_artifact(c_req)
                
            # Now run the master report renderer
            result = update_and_render_master_report(test_store)
            print("=== GENERATED MASTER REPORT MARKDOWN ===")
            print(result.full_markdown)
            
            # Simple assertions to ensure "None" didn't sneak in for the fields
            assert "Test Decision" in result.full_markdown
            assert "Decision Summary" in result.full_markdown
            assert "Goal Description" in result.full_markdown
            assert "Risk Description" in result.full_markdown
            assert "None" not in result.full_markdown.replace("* None", "") # Ignore empty sections
            
            print("\nSUCCESS: E2E Verification Passed. Real content found, no 'None' values.")

if __name__ == "__main__":
    run()
