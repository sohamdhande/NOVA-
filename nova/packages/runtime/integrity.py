import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List

from nova.packages.compiler import KnowledgeCommit
from nova.packages.runtime.store import KnowledgeStore

def _parse_iso(s: Any) -> Optional[datetime]:
    if isinstance(s, datetime):
        return s
    if not isinstance(s, str) or not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def _extract_content(meta: dict[str, Any]) -> dict[str, Any]:
    c = meta.get("content", meta)
    if isinstance(c, str):
        try:
            c = json.loads(c)
        except Exception:
            c = {"content": c}
    if not isinstance(c, dict):
        c = {"content": str(c)}
    return c

@dataclass(frozen=True)
class KnowledgeQualityProfile:
    node_id: str
    type: str
    evidence_strength: float
    evidence_count: int
    provenance_depth: int
    temporal_freshness: str
    review_status: str
    compiler_confidence: float
    knowledge_status: str
    integrity_flags: List[str]
    verification_status: str = "unverified"

@dataclass(frozen=True)
class ContradictionReport:
    type: str
    objects_involved: List[str]
    supporting_evidence: str
    timeline: List[str]
    confidence: float

@dataclass(frozen=True)
class IntegritySnapshot:
    snapshot_id: str
    generated_at: str
    commit_range: list[str]
    snapshot_hash: str
    health_score: float
    evidence_coverage: float
    freshness: float
    consistency: float
    contradictions: List[dict]
    profiles: Dict[str, dict]
    lonely_knowledge: List[dict]


def compute_integrity_snapshot(store: KnowledgeStore) -> dict:
    chain = store.get_chain()
    now = datetime.now(timezone.utc)

    # State tracking
    node_history: Dict[str, List[dict]] = {}
    latest_nodes: Dict[str, dict] = {}
    all_relationships: List[dict] = []
    action_items_by_goal: Dict[str, List[str]] = {}
    action_items_by_decision: Dict[str, List[str]] = {}

    for commit in chain:
        c_hash = commit.commit_hash
        c_ts = commit.created_at.isoformat() if hasattr(commit.created_at, "isoformat") else str(commit.created_at)
        c_dt = _parse_iso(commit.created_at) or now

        for node in commit.kir_nodes:
            meta = node.metadata or {}
            c_dict = _extract_content(meta)
            st_type = str(meta.get("type", meta.get("semantic_type", "UNKNOWN"))).upper()

            trace_item = {
                "id": node.output_id,
                "commit_hash": c_hash,
                "timestamp": c_ts,
                "dt": c_dt,
                "type": st_type,
                "title": c_dict.get("title", c_dict.get("description", c_dict.get("question", c_dict.get("statement", node.output_id)))),
                "supporting_artifact": meta.get("source_path", c_dict.get("supporting_artifact", "")),
                "supporting_observations": c_dict.get("supporting_observations", []),
                "confidence": meta.get("confidence", c_dict.get("confidence")),
                "evidence_span": meta.get("evidence_span", c_dict.get("evidence_span", "")),
                "status": str(meta.get("status", c_dict.get("status", "open"))).lower(),
                "content": c_dict,
                "verification_status": getattr(node, "verification_status", "unverified")
            }

            if trace_item["id"] not in node_history:
                node_history[trace_item["id"]] = []
            node_history[trace_item["id"]].append(trace_item)
            latest_nodes[trace_item["id"]] = trace_item

            if st_type == "RELATIONSHIP":
                all_relationships.append(trace_item)
            if st_type == "ACTION_ITEM":
                # Check for linkages
                rel_goal = c_dict.get("related_goal")
                rel_dec = c_dict.get("related_decision")
                if rel_goal:
                    action_items_by_goal.setdefault(rel_goal, []).append(trace_item["id"])
                if rel_dec:
                    action_items_by_decision.setdefault(rel_dec, []).append(trace_item["id"])

    profiles = {}
    lonely_knowledge = []
    contradictions = []

    lineage_edges = getattr(store, "get_lineage_edges", lambda: [])()
    lineage_supersessions = {}
    
    for edge in lineage_edges:
        if edge["verb"].upper() == "SUPERSEDES":
            lin_info = getattr(store, "get_node_lineage", lambda x: None)(edge["to_id"])
            if lin_info:
                lin_id = lin_info["lineage_id"]
                edge_dt = _parse_iso(edge["created_at"]) or now
                lineage_supersessions.setdefault(lin_id, []).append(edge_dt)
                
    volatile_lineages = set()
    for lin_id, times in lineage_supersessions.items():
        if len(times) >= 3:
            times.sort()
            for i in range(len(times) - 2):
                if (times[i+2] - times[i]).days <= 14:
                    volatile_lineages.add(lin_id)
                    break

    total_evidence_score = 0
    total_freshness_score = 0
    total_consistency_score = 0
    scored_nodes = 0

    for node_id, latest in latest_nodes.items():
        if latest["type"] in ["UNKNOWN", "RELATIONSHIP", "OBSERVATION", "ENTITY", "ARTIFACT"]:
            continue

        history = node_history[node_id]
        prov_depth = len(history)

        # Evidence Count
        artifacts = set()
        obs = set()
        for h in history:
            if h["supporting_artifact"]: artifacts.add(h["supporting_artifact"])
            for o in h["supporting_observations"]: obs.add(o)

        ev_count = len(artifacts) + len(obs)

        # Evidence Strength (0-100)
        base = 20
        art_score = min(40, len(artifacts) * 20)
        obs_score = min(20, len(obs) * 10)
        prov_score = min(10, (prov_depth - 1) * 5)
        
        flags = []
        is_lonely = False
        
        if latest["confidence"] is None:
            conf_score = 0
            flags.append("Confidence unspecified")
        else:
            conf_score = 10 if latest["confidence"] >= 0.85 else 0

        ev_strength = float(base + art_score + obs_score + prov_score + conf_score)

        # Temporal Freshness
        age_days = (now - latest["dt"]).days
        if age_days < 7:
            freshness = "Recently Updated"
        elif age_days < 30:
            freshness = "Recently Reviewed"
        elif age_days < 90:
            freshness = "Stale"
        else:
            freshness = "Dormant"

        # Knowledge Status
        status_field = latest["status"]
        if latest["verification_status"] == "verified":
            k_status = "Verified"
        elif status_field in ["completed", "closed", "resolved", "answered", "archived"]:
            k_status = "Archived"
        elif status_field in ["deprecated", "invalidated", "false"]:
            k_status = "Deprecated"
        elif status_field in ["superseded", "replaced"]:
            k_status = "Superseded"
        elif ev_strength > 80:
            k_status = "EvidenceStrong"
        elif ev_strength >= 50:
            k_status = "Supported"
        elif age_days >= 30:
            k_status = "Stale"
        else:
            k_status = "Emerging"

        if latest["type"] == "DECISION":
            if ev_count == 0:
                flags.append("Decision without supporting evidence")
            # Lonely: Decision with no goals, actions, or follow-ups
            if node_id not in action_items_by_decision:
                # also check relations
                linked = [r for r in all_relationships if r["content"].get("source") == node_id or r["content"].get("target") == node_id]
                if not linked:
                    flags.append("Lonely Knowledge: Decision exists in isolation")
                    is_lonely = True

        elif latest["type"] == "GOAL":
            if node_id not in action_items_by_goal:
                flags.append("Goal with no related action items")
                flags.append("Lonely Knowledge: Goal has no execution path")
                is_lonely = True

        elif latest["type"] == "RISK":
            if k_status not in ["Archived", "Deprecated", "Superseded"]:
                if not latest["content"].get("mitigation"):
                    flags.append("Risk without mitigation")

        elif latest["type"] == "QUESTION":
            if status_field in ["unresolved", "open"] and age_days > 14:
                flags.append("Question remaining unresolved beyond threshold")

        elif latest["type"] == "ASSUMPTION":
            if status_field in ["assumption", "unvalidated"] and age_days > 30:
                flags.append("Assumption never validated")

        if is_lonely:
            lonely_knowledge.append({
                "id": node_id,
                "type": latest["type"],
                "title": latest["title"],
                "reason": flags[-1],
                "timestamp": latest["timestamp"]
            })

        lin_info = getattr(store, "get_node_lineage", lambda x: None)(node_id)
        if lin_info and lin_info["lineage_id"] in volatile_lineages:
            flags.append("Volatile Lineage: 3+ supersessions within 14 days")

        profile = KnowledgeQualityProfile(
            node_id=node_id,
            type=latest["type"],
            evidence_strength=ev_strength,
            evidence_count=ev_count,
            provenance_depth=prov_depth,
            temporal_freshness=freshness,
            review_status="Approved" if "extracted_by_ai" not in latest["content"] else "Pending",
            compiler_confidence=latest["confidence"],
            knowledge_status=k_status,
            integrity_flags=flags,
            verification_status=latest["verification_status"]
        )
        profiles[node_id] = asdict(profile)

        scored_nodes += 1
        total_evidence_score += ev_strength
        if freshness in ["Recently Updated", "Recently Reviewed"]:
            total_freshness_score += 100
        elif freshness == "Stale":
            total_freshness_score += 50
        else:
            total_freshness_score += 10
            
        if not flags:
            total_consistency_score += 100
        elif is_lonely:
            total_consistency_score += 70
        else:
            total_consistency_score += max(0, 100 - (len(flags) * 20))

    # Cross-Type Contradiction Detection
    for r in all_relationships:
        if str(r["content"].get("relation", "")).upper() == "CONTRADICTS":
            src = r["content"].get("source")
            tgt = r["content"].get("target")
            if src in latest_nodes and tgt in latest_nodes:
                src_node = latest_nodes[src]
                tgt_node = latest_nodes[tgt]
                # If they are different types, or both decisions
                combo = {src_node["type"], tgt_node["type"]}
                c_type = f"{src_node['type']} vs {tgt_node['type']} Conflict"
                if "PRINCIPLE" in combo and "DECISION" in combo:
                    c_type = "Principle conflicts with Decision"
                elif "ASSUMPTION" in combo and "OBSERVATION" in combo:
                    c_type = "Assumption invalidated by Evidence"
                elif "GOAL" in combo and "CONSTRAINT" in combo:
                    c_type = "Goal conflicts with Constraint"
                elif "TRADEOFF" in combo and "DECISION" in combo:
                    c_type = "Trade-off contradicts Decision"
                elif "DECISION" in combo and len(combo) == 1:
                    c_type = "Mutually exclusive Decisions"

                contradictions.append(asdict(ContradictionReport(
                    type=c_type,
                    objects_involved=[src, tgt],
                    supporting_evidence=r["supporting_artifact"],
                    timeline=[src_node["timestamp"], tgt_node["timestamp"]],
                    confidence=min(src_node["confidence"], tgt_node["confidence"])
                )))

    # Identify implicit contradictions (e.g. Assumption invalidated by later evidence without explicit relation)
    # Simple deterministic heuristic: if Assumption status is invalid but a decision relies on it.
    for n_id, p in profiles.items():
        if p["knowledge_status"] == "Conflicted":
            # Just marking it
            pass

    evidence_coverage = (total_evidence_score / scored_nodes) if scored_nodes > 0 else 100.0
    freshness_score = (total_freshness_score / scored_nodes) if scored_nodes > 0 else 100.0
    consistency_score = (total_consistency_score / scored_nodes) if scored_nodes > 0 else 100.0

    # Contradiction penalty
    c_penalty = min(40, len(contradictions) * 10)
    health_score = max(0.0, min(100.0, ((evidence_coverage + freshness_score + consistency_score) / 3) - c_penalty))

    commit_range = [c.commit_hash for c in chain]
    range_bounds = [commit_range[0], commit_range[-1]] if len(commit_range) >= 2 else (commit_range * 2 if commit_range else ["none", "none"])

    raw_dict = {
        "commit_range": range_bounds,
        "health_score": round(health_score, 1),
        "evidence_coverage": round(evidence_coverage, 1),
        "freshness": round(freshness_score, 1),
        "consistency": round(consistency_score, 1),
        "contradictions": contradictions,
        "profiles": profiles,
        "lonely_knowledge": lonely_knowledge
    }
    
    report_json = json.dumps(raw_dict, sort_keys=True)
    report_hash = hashlib.sha256(report_json.encode("utf-8")).hexdigest()

    return asdict(IntegritySnapshot(
        snapshot_id=f"integ_{report_hash[:12]}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        snapshot_hash=report_hash,
        **raw_dict
    ))
