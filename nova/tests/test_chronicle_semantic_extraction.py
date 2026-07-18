import pytest
from datetime import datetime, timezone
from nova.packages.ontology import SemanticType
from nova.packages.llm.models import (
    DecisionSuggestion, RiskSuggestion, AssumptionSuggestion,
    TradeoffSuggestion, AlternativeSuggestion, GoalSuggestion,
    QuestionSuggestion, PrincipleSuggestion, StructuredExtractionResult,
    MarketDataSuggestion, CompetitorSuggestion, TeamMemberSuggestion,
    FinancialMetricSuggestion
)
from nova.packages.llm import get_provider
from nova.packages.observation import build_bundle, build_multi_bundle
from nova.packages.compiler import compile as nova_compile
from nova.packages.identity import IdentityRegistry
from nova.packages.temporal import TemporalIndex
from nova.packages.provenance import ProvenanceGraph
from nova.packages.reasoning import (
    build_plan, analyze_dependencies, lower_to_reasoning_ir, optimize_reasoning_ir
)
from nova.packages.runtime import KnowledgeStore, Projection


def test_suggestion_models_and_evidence_spans():
    dec = DecisionSuggestion(title="Use SQLite", summary="Datastore choice", evidence_span="Lines 14-18", confidence=0.92)
    assert dec.evidence_span == "Lines 14-18"
    assert dec.confidence == 0.92

    risk = RiskSuggestion(description="Downtime risk", category="Deployment", evidence_span="Line 25", confidence=0.85)
    assert risk.category == "Deployment"

    ass = AssumptionSuggestion(description="Under 10k users", evidence_span="Line 20", confidence=0.88)
    trade = TradeoffSuggestion(side_a="Speed", side_b="Cost", description="Latency vs Dollar", evidence_span="Line 15", confidence=0.89)
    alt = AlternativeSuggestion(topic="DB choice", options=["SQLite", "Postgres"], chosen_option="SQLite", evidence_span="Lines 10-12", confidence=0.9)
    goal = GoalSuggestion(description="20% latency drop", evidence_span="Line 5", confidence=0.95)
    ques = QuestionSuggestion(question="Redis caching?", evidence_span="Line 35", confidence=0.87)
    prin = PrincipleSuggestion(statement="Single semantic authority", evidence_span="Line 1", confidence=0.99)

    market = MarketDataSuggestion(metric="TAM", value=1000, unit="USD", evidence_span="Line 1", confidence=0.9)
    comp = CompetitorSuggestion(name="Rival Inc", category="direct", evidence_span="Line 2", confidence=0.8)
    team = TeamMemberSuggestion(name="Alice", role="CEO", is_founder=True, evidence_span="Line 3", confidence=0.9)
    fin = FinancialMetricSuggestion(metric_type="burn_rate", value=50000, unit="USD", evidence_span="Line 4", confidence=0.95)

    res = StructuredExtractionResult(
        decisions=[dec], risks=[risk], assumptions=[ass],
        tradeoffs=[trade], alternatives=[alt], goals=[goal],
        questions=[ques], principles=[prin], market_data=[market],
        competitors=[comp], team_members=[team], financial_metrics=[fin]
    )
    assert len(res.decisions) == 1
    assert len(res.principles) == 1
    assert len(res.market_data) == 1
    assert res.market_data[0].metric == "TAM"
    assert res.competitors[0].name == "Rival Inc"
    assert res.team_members[0].is_founder is True
    assert res.financial_metrics[0].value == 50000


def test_provider_orchestrated_extraction():
    provider = get_provider()
    # Mock inference fallback returns all categories
    extracted = provider.extract_organizational_knowledge("We decided to migrate to Postgres", "spec/db.md", "plaintext")
    assert "decisions" in extracted
    assert len(extracted["decisions"]) > 0
    assert extracted["decisions"][0]["evidence_span"] == "Lines 14-18"


def test_first_class_ontology_types():
    assert SemanticType.CONSTRAINT.value == "CONSTRAINT"
    assert SemanticType.TRADEOFF.value == "TRADEOFF"
    assert SemanticType.ALTERNATIVE.value == "ALTERNATIVE"
    assert SemanticType.QUESTION.value == "QUESTION"
    assert SemanticType.ACTION_ITEM.value == "ACTION_ITEM"
    assert SemanticType.PRINCIPLE.value == "PRINCIPLE"
    assert SemanticType.MARKET_DATA.value == "MARKET_DATA"
    assert SemanticType.COMPETITOR.value == "COMPETITOR"
    assert SemanticType.TEAM_MEMBER.value == "TEAM_MEMBER"
    assert SemanticType.FINANCIAL_METRIC.value == "FINANCIAL_METRIC"


def test_multi_bundle_and_compiler_compatibility():
    id_reg = IdentityRegistry()
    temp_idx = TemporalIndex()
    prov = ProvenanceGraph()

    items = [
        {"id": "sug_dec_1", "type": "DECISION", "content": {"title": "Adopt Postgres", "evidence_span": "Line 1"}},
        {"id": "sug_risk_1", "type": "RISK", "content": {"description": "Migration delay", "evidence_span": "Line 2"}},
        {"id": "sug_ques_1", "type": "QUESTION", "content": {"question": "Cache strategy?", "evidence_span": "Line 3"}}
    ]

    bundle = build_multi_bundle(items, id_reg, temp_idx, prov)
    assert len(bundle.observations) == 3
    assert bundle.observations[0].type == SemanticType.DECISION
    assert bundle.observations[1].type == SemanticType.RISK
    assert bundle.observations[2].type == SemanticType.QUESTION

    # Run locked deterministic NOVA compiler
    commit = nova_compile(bundle)
    assert commit.commit_hash is not None
    assert len(commit.kir_nodes) == 3
    assert commit.kir_nodes[0].metadata["type"] == "DECISION"


def test_reasoning_preferential_ranking():
    store = KnowledgeStore()
    id_reg = IdentityRegistry()
    temp_idx = TemporalIndex()
    prov = ProvenanceGraph()

    items = [
        {"id": "obs_gen", "type": "OBSERVATION", "content": {"text": "Discussing sqlite database performance"}},
        {"id": "obs_dec", "type": "DECISION", "content": {"title": "Chose sqlite database for simplicity", "semantic_type": "DECISION"}},
        {"id": "obs_trade", "type": "TRADEOFF", "content": {"description": "sqlite database concurrency vs local speed", "semantic_type": "TRADEOFF"}}
    ]
    bundle = build_multi_bundle(items, id_reg, temp_idx, prov)
    commit = nova_compile(bundle)
    store.commit(commit)

    facts = [n.metadata for n in commit.kir_nodes]
    proj = Projection(facts=facts, as_of=datetime.now(timezone.utc))

    plan = build_plan("Why did we choose sqlite database?")
    analysis = analyze_dependencies(plan, proj)
    rir = lower_to_reasoning_ir(analysis, proj, plan)
    rir_opt = optimize_reasoning_ir(rir)

    # Verify DECISION and TRADEOFF appear before generic OBSERVATION
    assert len(rir_opt.selected_facts) >= 2
    types_ordered = [f.get("type") for f in rir_opt.selected_facts]
    assert types_ordered[0] == "DECISION"
    assert types_ordered[1] == "TRADEOFF"


if __name__ == "__main__":
    pytest.main([__file__])
