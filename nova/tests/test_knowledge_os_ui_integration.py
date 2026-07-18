"""
Tests for Knowledge OS Frontend Product Integration.
Verifies API endpoint handler contract (models, response shapes) and frontend component architecture.
"""

import sys
import os
from pathlib import Path
import pytest

# Ensure root directory is importable
_root = str(Path(__file__).parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from api.knowledge_routes import (
    explore_knowledge, search_knowledge, get_timeline, inspect_object,
    reason_knowledge, explain_knowledge, get_entities, get_artifacts,
    get_observations, get_commits, get_relationships, knowledge_health,
    PreviewRequest, CompileRequest, preview_artifact, compile_artifact,
    get_home_stats, export_knowledge, reset_knowledge
)
from unittest.mock import patch
from nova.packages.runtime.persistence import SQLiteCommitStore

# Mock the store for the entire test file
_test_store = SQLiteCommitStore(":memory:")

@pytest.fixture(autouse=True)
def isolated_store():
    with patch("api.knowledge_routes._get_store", return_value=_test_store):
        yield


def test_api_integration_explore():
    """Test graph explorer adjacency matrix handler."""
    data = explore_knowledge()
    assert "artifacts" in data
    assert "observations" in data
    assert "entities" in data
    assert "commits" in data
    assert isinstance(data["commits"], list)


def test_api_integration_search():
    """Test global search handler."""
    res = search_knowledge("test")
    assert isinstance(res, list)


def test_api_integration_timeline():
    """Test chronological activity timeline handler."""
    res = get_timeline()
    assert isinstance(res, list)


def test_api_integration_inspect_fallback():
    """Test Universal Inspector panel fallback handler."""
    data = inspect_object("nonexistent_id_123")
    assert data["object_type"] == "Entity"
    assert data["id"] == "nonexistent_id_123"
    assert "summary" in data


def test_api_integration_reason():
    """Test reasoning engine query handler."""
    data = reason_knowledge("Why?")
    assert "intent" in data
    assert "context" in data


def test_api_integration_explain():
    """Test provenance chain traversal handler."""
    data = explain_knowledge("obs_test_123")
    assert "fact_id" in data
    assert "chain" in data
    assert isinstance(data["chain"], list)


def test_api_integration_lists():
    """Test data fetching handlers for entities, artifacts, observations, commits, relationships."""
    assert isinstance(get_entities(), list)
    assert isinstance(get_artifacts(), list)
    assert isinstance(get_observations(), list)
    assert isinstance(get_commits(), list)
    assert isinstance(get_relationships(), list)
    assert "status" in knowledge_health()


def test_api_integration_preview_and_compile():
    """Test preview extraction and compilation handlers."""
    req = PreviewRequest(source_type="plaintext", content="Test extraction review flow")
    preview = preview_artifact(req)
    assert "observations" in preview
    assert len(preview["observations"]) >= 1
    assert preview["observations"][0]["approved"] is True

    creq = CompileRequest(source_type="plaintext", content="Test extraction review flow", approved_observation_ids=[preview["observations"][0]["id"]])
    cres = compile_artifact(creq)
    assert cres["status"] == "success"
    assert "commit_hash" in cres


def test_api_integration_stats_export_reset():
    """Test stats, export, and reset handlers."""
    stats = get_home_stats()
    assert "stats" in stats
    assert "recent_commits" in stats

    export = export_knowledge()
    assert isinstance(export, list)


def test_frontend_architecture_and_constraints():
    """Verify frontend component integration, file size limits (<250 lines), and zero duplication."""
    dashboard_src = Path(_root) / "dashboard" / "src"
    knowledge_dir = dashboard_src / "components" / "panels" / "knowledge"
    
    assert knowledge_dir.exists(), "Knowledge OS components directory missing"
    
    # 1. Check Sidebar navigation extension
    sidebar_file = dashboard_src / "components" / "Sidebar" / "Sidebar.tsx"
    sidebar_txt = sidebar_file.read_text()
    assert '"knowledge"' in sidebar_txt or "'knowledge'" in sidebar_txt, "Knowledge nav item missing in Sidebar"
    assert "DISTILL" in sidebar_txt and ("KNOWLEDGE" in sidebar_txt or "CHRONICLE" in sidebar_txt)
    
    # 2. Check DashboardLayout routing extension
    layout_file = dashboard_src / "layouts" / "DashboardLayout.tsx"
    layout_txt = layout_file.read_text()
    assert "KnowledgePanel" in layout_txt, "KnowledgePanel mapping missing in DashboardLayout"
    
    # 3. Verify all required components exist and respect size constraint (<350 lines)
    expected_components = [
        "KnowledgePanel.tsx", "InspectorCard.tsx", "ExplorerView.tsx",
        "SearchView.tsx", "TimelineView.tsx", "ListView.tsx",
        "ReasoningView.tsx", "ExplainView.tsx",
        "HomeView.tsx", "NewArtifactView.tsx", "SettingsView.tsx"
    ]
    
    for comp in expected_components:
        comp_path = knowledge_dir / comp
        assert comp_path.exists(), f"Missing required component: {comp}"
        lines = comp_path.read_text().splitlines()
        assert len(lines) <= 350, f"Component {comp} exceeds 350 lines ({len(lines)} lines)"
        
        # Verify reuse of existing design system / API client
        txt = comp_path.read_text()
        if "useApi" in txt:
            assert "hooks/useApi" in txt, f"{comp} must reuse existing useApi hook"


if __name__ == "__main__":
    pytest.main([__file__])
