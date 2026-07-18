import json
from datetime import datetime, timezone
from nova.packages.runtime.persistence import SQLiteCommitStore
from nova.packages.runtime.daily_chronicle import generate_daily_chronicle, compute_knowledge_health
from nova.packages.compiler import KnowledgeCommit
from nova.packages.kir import KIRNode, Dialect
from nova.packages.reasoning import compile_reasoning_context


def _make_commit(hash_id: str, parent: str, nodes_meta: list[dict]) -> KnowledgeCommit:
    nodes = []
    for idx, m in enumerate(nodes_meta):
        nodes.append(KIRNode(
            op="ASSERT",
            inputs=[],
            output_id=f"kir_{hash_id}_{idx}",
            metadata=m,
            dialect=Dialect.DECISION if m.get("type") == "DECISION" else Dialect.GENERIC
        ))
    return KnowledgeCommit(
        commit_hash=hash_id,
        parent_hash=parent,
        kir_nodes=nodes,
        created_at=datetime.now(timezone.utc)
    )


def test_daily_chronicle_pure_facts():
    store = SQLiteCommitStore(":memory:")
    c1 = _make_commit("hash_c1", None, [
        {"type": "DECISION", "content": {"title": "Use SQLite", "rationale": "Fast local DB", "participants": ["eng"]}, "source_path": "docs/arch.md"},
        {"type": "RISK", "content": {"title": "Concurrency", "severity": "high", "supporting_evidence": "Lock contention"}},
        {"type": "ASSUMPTION", "content": {"title": "Single user", "status": "validated"}}
    ])
    store.commit(c1)

    report = generate_daily_chronicle(store, window="all")
    
    # 1. Check Snapshot ID and Hash reproducibility
    snap = report["snapshot"]
    assert snap["snapshot_id"].startswith("snap_")
    assert len(snap["report_hash"]) == 64
    assert snap["window"] == "all"

    # 2. Check pure facts lists
    assert len(report["new_decisions"]) == 1
    assert report["new_decisions"][0]["title"] == "Use SQLite"
    assert report["new_decisions"][0]["rationale"] == "Fast local DB"

    assert len(report["new_risks"]) == 1
    assert report["new_risks"][0]["severity"] == "high"

    assert len(report["assumption_changes"]["validated"]) == 1
    assert report["assumption_changes"]["validated"][0]["title"] == "Single user"

    # 3. Check growth stats
    growth = report["chronicle_growth"]
    assert growth["commits"] == 1
    assert growth["semantic_objects_added"] == 3


def test_knowledge_health_monitoring():
    store = SQLiteCommitStore(":memory:")
    c1 = _make_commit("hash_h1", None, [
        # Weak evidence (< 0.85 conf)
        {"type": "DECISION", "confidence": 0.5, "evidence_span": "", "content": {"title": "Unsupported Dec"}},
        # Unresolved question
        {"type": "QUESTION", "evidence_span": "Lines 1-5", "content": {"question": "Auth scheme?", "status": "unresolved"}},
        # Goal w/o progress
        {"type": "GOAL", "evidence_span": "Lines 1-5", "content": {"title": "Launch", "status": "active", "progress": 0}}
    ])
    store.commit(c1)

    health = compute_knowledge_health(store)

    assert health["total_issues"] >= 3
    assert len(health["weak_evidence"]) == 1
    assert len(health["unresolved_questions"]) == 1
    assert len(health["goals_without_progress"]) == 1
    assert health["health_zone"] in ["STABLE", "DEGRADED", "CRITICAL"]


def test_preferential_reasoning_integration():
    store = SQLiteCommitStore(":memory:")
    c1 = _make_commit("hash_r1", None, [
        {"type": "DECISION", "content": {"title": "OAuth2 Auth", "rationale": "Standard security"}}
    ])
    store.commit(c1)

    exec_context = compile_reasoning_context("What happened this week?", store)

    # Verify DAILY_CHRONICLE_REPORT fact is compiled at top priority
    assert "DAILY_CHRONICLE_REPORT" in exec_context
    assert "snap_" in exec_context
