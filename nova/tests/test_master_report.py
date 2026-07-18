import pytest
from datetime import datetime, timezone, timedelta

from nova.packages.runtime.persistence import SQLiteCommitStore
from nova.packages.runtime.state_resolution import ResolvedNode, StateSnapshot
from nova.packages.kir import KIRNode, Dialect
from nova.packages.runtime.master_report import hash_category_nodes, get_changed_categories, update_and_render_master_report, render_master_report_pdf
from unittest.mock import patch, MagicMock


def create_test_node(output_id="kir_1"):
    return KIRNode(
        op="DECISION",
        inputs=[],
        output_id=output_id,
        metadata={"type": "DECISION", "content": {"title": "Test"}},
        dialect=Dialect.GENERIC
    )


def test_hash_category_nodes_deterministic():
    node1 = ResolvedNode(
        node=create_test_node("kir_1"),
        status="ACTIVE",
        superseded_by=None,
        first_committed_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc)
    )
    
    node2 = ResolvedNode(
        node=create_test_node("kir_2"),
        status="SUPERSEDED",
        superseded_by="kir_3",
        first_committed_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc)
    )
    
    nodes = [node2, node1]  # pass in mixed order
    
    hash1 = hash_category_nodes(nodes)
    hash2 = hash_category_nodes(nodes)
    
    assert hash1 == hash2, "Hash should be completely deterministic for identical inputs"


def test_hash_ignores_timestamps_and_catches_status_changes():
    now = datetime.now(timezone.utc)
    node1_v1 = ResolvedNode(
        node=create_test_node("kir_1"),
        status="ACTIVE",
        superseded_by=None,
        first_committed_at=now,
        last_updated_at=now
    )
    
    node1_v2 = ResolvedNode(
        node=create_test_node("kir_1"),
        status="ACTIVE",
        superseded_by=None,
        first_committed_at=now - timedelta(days=1),
        last_updated_at=now + timedelta(days=1)
    )
    
    assert hash_category_nodes([node1_v1]) == hash_category_nodes([node1_v2]), "Timestamps should be excluded from hash"
    
    node1_superseded = ResolvedNode(
        node=create_test_node("kir_1"),
        status="SUPERSEDED",
        superseded_by="kir_3",
        first_committed_at=now,
        last_updated_at=now
    )
    
    assert hash_category_nodes([node1_v1]) != hash_category_nodes([node1_superseded]), "Status change must alter hash"


def test_get_changed_categories():
    store = SQLiteCommitStore(":memory:")
    
    # 1. Create a snapshot with some data
    nodes = [ResolvedNode(
        node=create_test_node("kir_1"),
        status="ACTIVE",
        superseded_by=None,
        first_committed_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc)
    )]
    
    snapshot = StateSnapshot(
        buckets={"DECISION": nodes},
        generated_from_chain_length=1,
        category_counts={"DECISION": 1}
    )
    
    # Empty cache -> needs re-render
    changed = get_changed_categories(store, snapshot)
    assert changed.get("DECISION") is True, "Should require render when cache is empty"
    
    # Save the section cache
    target_hash = hash_category_nodes(nodes)
    store.save_section("DECISION", target_hash, "# Markdown content")
    
    # Run diff again
    changed_again = get_changed_categories(store, snapshot)
    assert changed_again.get("DECISION") is False, "Should not require render if cache matches exactly"
    
    # Change the node (simulate superseded)
    nodes[0] = ResolvedNode(
        node=create_test_node("kir_1"),
        status="SUPERSEDED",
        superseded_by="kir_new",
        first_committed_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc)
    )
    
    snapshot_new = StateSnapshot(
        buckets={"DECISION": nodes},
        generated_from_chain_length=1,
        category_counts={"DECISION": 1}
    )
    
    # Run diff again with modified data
    changed_final = get_changed_categories(store, snapshot_new)
    assert changed_final.get("DECISION") is True, "Should require render when content hash changes"

def test_update_and_render_master_report():
    store = SQLiteCommitStore(":memory:")
    
    # We mock get_state_snapshot to control the data
    with patch("nova.packages.runtime.master_report.get_state_snapshot") as mock_get_snapshot, \
         patch("nova.packages.runtime.master_report.datetime") as mock_dt:
        
        # Freeze time so generated_at is constant and report_hash matches
        fixed_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        mock_dt.now.return_value = fixed_now
        mock_dt.timezone = timezone
        
        # Test 1: First render, everything should re-render
        dec_node = ResolvedNode(
            node=KIRNode(op="TEST", inputs=[], output_id="kir_1", metadata={"type": "DECISION", "content": {"title": "Test1", "summary": "Desc"}}, dialect=Dialect.GENERIC),
            status="ACTIVE", superseded_by=None, first_committed_at=datetime.now(timezone.utc), last_updated_at=datetime.now(timezone.utc)
        )
        goal_node = ResolvedNode(
            node=KIRNode(op="TEST", inputs=[], output_id="kir_2", metadata={"type": "GOAL", "content": {"description": "Goal1"}}, dialect=Dialect.GENERIC),
            status="ACTIVE", superseded_by=None, first_committed_at=datetime.now(timezone.utc), last_updated_at=datetime.now(timezone.utc)
        )
        team_node = ResolvedNode(
            node=KIRNode(op="TEST", inputs=[], output_id="kir_3", metadata={"type": "TEAM_MEMBER", "content": {"name": "Bob"}}, dialect=Dialect.GENERIC),
            status="ACTIVE", superseded_by=None, first_committed_at=datetime.now(timezone.utc), last_updated_at=datetime.now(timezone.utc)
        )
        
        snapshot = StateSnapshot(
            buckets={"DECISION": [dec_node], "GOAL": [goal_node], "TEAM_MEMBER": [team_node]},
            generated_from_chain_length=1,
            category_counts={}
        )
        mock_get_snapshot.return_value = snapshot
        
        result1 = update_and_render_master_report(store)
        assert len(result1.sections_rerendered) == 12
        assert len(result1.sections_from_cache) == 0
        assert "Test1" in result1.full_markdown
        
        # Test 2: Unchanged data, everything from cache
        result2 = update_and_render_master_report(store)
        assert len(result2.sections_rerendered) == 0
        assert len(result2.sections_from_cache) == 12
        assert result1.report_hash == result2.report_hash
        
        # Test 3: Change ONE category (DECISION). Sections depending on DECISION should rerender, others should stay cached.
        dec_node2 = ResolvedNode(
            node=KIRNode(op="TEST", inputs=[], output_id="kir_4", metadata={"type": "DECISION", "content": {"title": "Test2", "summary": "Desc2"}}, dialect=Dialect.GENERIC),
            status="ACTIVE", superseded_by=None, first_committed_at=datetime.now(timezone.utc), last_updated_at=datetime.now(timezone.utc)
        )
        snapshot2 = StateSnapshot(
            buckets={"DECISION": [dec_node, dec_node2], "GOAL": [goal_node], "TEAM_MEMBER": [team_node]},
            generated_from_chain_length=2,
            category_counts={}
        )
        mock_get_snapshot.return_value = snapshot2
        
        result3 = update_and_render_master_report(store)
        
        # Which sections consume DECISION?
        # solution_product, business_model, go_to_market -> 3 sections.
        assert "solution_product" in result3.sections_rerendered
        assert "go_to_market" in result3.sections_rerendered
        assert "business_model" in result3.sections_rerendered
        assert len(result3.sections_rerendered) == 3
        
        # The remaining 9 should be from cache
        assert len(result3.sections_from_cache) == 9
        assert "team" in result3.sections_from_cache
        
        assert "Test2" in result3.full_markdown


@patch("nova.packages.runtime.master_report.create_pdf")
def test_render_master_report_pdf(mock_create_pdf, tmp_path):
    # Mock create_pdf to write a dummy PDF file and return its path
    dummy_pdf_path = tmp_path / "dummy.pdf"
    
    def mock_create(topic, content):
        with open(dummy_pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\n%Dummy PDF content")
        return str(dummy_pdf_path)
        
    mock_create_pdf.side_effect = mock_create
    
    # Create dummy result
    from nova.packages.runtime.master_report import MasterReportResult
    result = MasterReportResult(
        full_markdown="# Hello",
        report_hash="abc",
        generated_at=datetime.now(timezone.utc),
        sections_rerendered=[],
        sections_from_cache=[]
    )
    
    pdf_bytes = render_master_report_pdf(result)
    
    # Verify the bytes
    assert pdf_bytes.startswith(b"%PDF")
    
    # Verify cleanup
    assert not dummy_pdf_path.exists()

