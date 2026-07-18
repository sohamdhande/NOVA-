import pytest
from datetime import datetime, timezone
from nova.packages.runtime.state_resolution import ResolvedNode, StateSnapshot
from nova.packages.kir import KIRNode, Dialect
from nova.packages.runtime.master_report_renderers import (
    render_solution_product_section,
    render_go_to_market_section,
    render_roadmap_risks_section,
    render_executive_summary_section,
    render_business_model_section,
    render_market_opportunity_section,
    render_competitive_landscape_section,
    render_team_section,
    render_financials_ask_section,
    SECTION_RENDERERS
)

def _create_resolved(metadata: dict, output_id: str = "test_id") -> ResolvedNode:
    return ResolvedNode(
        node=KIRNode(
            op="TEST",
            inputs=[],
            output_id=output_id,
            metadata=metadata,
            dialect=Dialect.GENERIC
        ),
        status="ACTIVE",
        superseded_by=None,
        first_committed_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc)
    )

def test_render_solution_product_section():
    dec_node = _create_resolved({"type": "DECISION", "title": "Database", "summary": "Use Postgres"})
    tradeoff_node = _create_resolved({"type": "TRADEOFF", "side_a": "Speed", "side_b": "Cost", "description": "Faster but expensive"})
    alt_node = _create_resolved({"type": "ALTERNATIVE", "topic": "Framework", "chosen_option": "React"})
    
    snapshot = StateSnapshot(
        buckets={"DECISION": [dec_node], "TRADEOFF": [tradeoff_node], "ALTERNATIVE": [alt_node]},
        generated_from_chain_length=1,
        category_counts={}
    )
    
    out = render_solution_product_section(snapshot)
    assert "## Solution & Product" in out
    assert "**Database**: Use Postgres" in out
    assert "**Speed vs Cost**: Faster but expensive" in out
    assert "**Framework** -> Chose: React" in out


def test_render_go_to_market_section():
    dec_node = _create_resolved({"type": "DECISION", "title": "Pricing Strategy", "summary": "Freemium"})
    action_node = _create_resolved({"type": "ACTION_ITEM", "description": "Launch on Product Hunt"})
    
    snapshot = StateSnapshot(
        buckets={"DECISION": [dec_node], "ACTION_ITEM": [action_node]},
        generated_from_chain_length=1,
        category_counts={}
    )
    
    out = render_go_to_market_section(snapshot)
    assert "## Go-to-Market" in out
    assert "**Pricing Strategy**: Freemium" in out
    assert "Launch on Product Hunt" in out


def test_render_roadmap_risks_section():
    goal_node = _create_resolved({"type": "GOAL", "description": "Q3 Revenue Target"})
    action_node = _create_resolved({"type": "ACTION_ITEM", "description": "Hire Sales Lead"})
    risk_node = _create_resolved({"type": "RISK", "description": "Competitor out-pricing us"})
    question_node = _create_resolved({"type": "QUESTION", "question": "Are we legally compliant in EU?"})
    
    snapshot = StateSnapshot(
        buckets={
            "GOAL": [goal_node],
            "ACTION_ITEM": [action_node],
            "RISK": [risk_node],
            "QUESTION": [question_node],
        },
        generated_from_chain_length=1,
        category_counts={}
    )
    
    out = render_roadmap_risks_section(snapshot)
    assert "## Roadmap & Risks" in out
    assert "Q3 Revenue Target" in out
    assert "Hire Sales Lead" in out
    assert "Competitor out-pricing us" in out
    assert "Are we legally compliant in EU?" in out


def test_render_executive_summary_section_with_tags():
    prin_node = _create_resolved({"type": "PRINCIPLE", "statement": "Data democratized", "rationale": "For everyone", "is_foundational": True})
    goal_node = _create_resolved({"type": "GOAL", "description": "Become market leader"})
    
    snapshot = StateSnapshot(
        buckets={"PRINCIPLE": [prin_node], "GOAL": [goal_node]},
        generated_from_chain_length=1,
        category_counts={}
    )
    
    out = render_executive_summary_section(snapshot)
    assert "## Executive Summary" in out
    assert "Data democratized" in out
    assert "Become market leader" in out
    assert "No foundational principle has been marked yet" not in out

def test_render_executive_summary_section_missing_tags():
    prin_node = _create_resolved({"type": "PRINCIPLE", "statement": "Use singletons", "rationale": "Performance", "is_foundational": False})
    
    snapshot = StateSnapshot(
        buckets={"PRINCIPLE": [prin_node]},
        generated_from_chain_length=1,
        category_counts={}
    )
    
    out = render_executive_summary_section(snapshot)
    assert "## Executive Summary" in out
    assert "No foundational principle has been marked yet. Mark a PRINCIPLE as foundational to populate this section." in out
    assert "Use singletons" not in out

def test_render_business_model_section_with_tags():
    dec_node = _create_resolved({"type": "DECISION", "title": "SaaS Model", "summary": "10/mo", "decision_category": "pricing"})
    assump_node = _create_resolved({"type": "ASSUMPTION", "description": "Users will pay"})
    
    snapshot = StateSnapshot(
        buckets={"DECISION": [dec_node], "ASSUMPTION": [assump_node]},
        generated_from_chain_length=1,
        category_counts={}
    )
    
    out = render_business_model_section(snapshot)
    assert "## Business Model" in out
    assert "SaaS Model" in out
    assert "Users will pay" in out
    assert "No pricing-related decision has been marked yet" not in out

def test_render_business_model_section_missing_tags():
    dec_node = _create_resolved({"type": "DECISION", "title": "DB Choice", "summary": "Use Postgres"}) # no category
    
    snapshot = StateSnapshot(
        buckets={"DECISION": [dec_node]},
        generated_from_chain_length=1,
        category_counts={}
    )
    
    out = render_business_model_section(snapshot)
    assert "## Business Model" in out
    assert "No pricing-related decision has been marked yet. Extract a DECISION with decision_category='pricing' to populate this section." in out
    assert "DB Choice" not in out


def test_section_renderers_registry():
    assert len(SECTION_RENDERERS) == 12
    
    expected_keys = [
        "solution_product", "business_model", "traction_milestones",
        "go_to_market", "roadmap_risks", "the_problem", "why_now", "executive_summary",
        "market_opportunity", "competitive_landscape", "team", "financials_ask"
    ]
    
    for key in expected_keys:
        assert key in SECTION_RENDERERS
        
    func, categories = SECTION_RENDERERS["solution_product"]
    assert callable(func)
    assert "DECISION" in categories

def test_market_opportunity_populated():
    node = _create_resolved({"type": "MARKET_DATA", "metric": "TAM", "value": 100, "unit": "M USD"})
    snapshot = StateSnapshot(buckets={"MARKET_DATA": [node]}, generated_from_chain_length=1, category_counts={})
    out = render_market_opportunity_section(snapshot)
    assert "TAM" in out
    assert "100" in out

def test_market_opportunity_empty_no_signal():
    snapshot = StateSnapshot(buckets={}, generated_from_chain_length=1, category_counts={})
    out = render_market_opportunity_section(snapshot)
    assert "Market sizing (TAM/SAM/SOM) has not yet been recorded" in out

def test_market_opportunity_empty_with_signal():
    q_node = _create_resolved({"type": "QUESTION", "question": "What is our TAM?"})
    snapshot = StateSnapshot(buckets={"QUESTION": [q_node]}, generated_from_chain_length=1, category_counts={})
    out = render_market_opportunity_section(snapshot)
    assert "Open Question test_id" in out
    assert "What is our TAM?" in out

def test_competitive_landscape_populated():
    node = _create_resolved({"type": "COMPETITOR", "name": "Rival", "category": "direct"})
    snapshot = StateSnapshot(buckets={"COMPETITOR": [node]}, generated_from_chain_length=1, category_counts={})
    out = render_competitive_landscape_section(snapshot)
    assert "Rival" in out
    assert "direct" in out

def test_competitive_landscape_empty_no_signal():
    snapshot = StateSnapshot(buckets={}, generated_from_chain_length=1, category_counts={})
    out = render_competitive_landscape_section(snapshot)
    assert "Competitive landscape has not yet been recorded" in out

def test_competitive_landscape_empty_with_signal():
    r_node = _create_resolved({"type": "RISK", "description": "Big competitor is releasing a feature"})
    snapshot = StateSnapshot(buckets={"RISK": [r_node]}, generated_from_chain_length=1, category_counts={})
    out = render_competitive_landscape_section(snapshot)
    assert "Risk test_id references competitive pressure" in out
    assert "Big competitor is releasing" in out

def test_team_populated():
    n1 = _create_resolved({"type": "TEAM_MEMBER", "name": "Bob", "is_founder": False}, output_id="id1")
    n2 = _create_resolved({"type": "TEAM_MEMBER", "name": "Alice", "is_founder": True}, output_id="id2")
    snapshot = StateSnapshot(buckets={"TEAM_MEMBER": [n1, n2]}, generated_from_chain_length=1, category_counts={})
    out = render_team_section(snapshot)
    assert "Alice" in out
    assert "Bob" in out
    # Alice should be sorted first
    assert out.find("Alice") < out.find("Bob")

def test_team_empty():
    snapshot = StateSnapshot(buckets={}, generated_from_chain_length=1, category_counts={})
    out = render_team_section(snapshot)
    assert "Team composition and founder backgrounds have not yet been recorded" in out

def test_financials_ask_populated():
    node = _create_resolved({"type": "FINANCIAL_METRIC", "metric_type": "burn rate", "value": 50000})
    snapshot = StateSnapshot(buckets={"FINANCIAL_METRIC": [node]}, generated_from_chain_length=1, category_counts={})
    out = render_financials_ask_section(snapshot)
    assert "burn rate" in out
    assert "50000" in out

def test_financials_ask_empty_no_signal():
    snapshot = StateSnapshot(buckets={}, generated_from_chain_length=1, category_counts={})
    out = render_financials_ask_section(snapshot)
    assert "Financial metrics and funding ask have not yet been recorded" in out

def test_financials_ask_empty_with_signal():
    g_node = _create_resolved({"type": "GOAL", "description": "Raise funding"})
    snapshot = StateSnapshot(buckets={"GOAL": [g_node]}, generated_from_chain_length=1, category_counts={})
    out = render_financials_ask_section(snapshot)
    assert "Goal test_id references funding" in out
    assert "Raise funding" in out
