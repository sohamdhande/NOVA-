import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from nova.packages.compiler import KnowledgeCommit
from nova.packages.runtime.store import KnowledgeStore


@dataclass(frozen=True)
class ChronicleSnapshot:
    snapshot_id: str
    generated_at: str
    window: str
    commit_range: list[str]
    report_hash: str


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


def filter_commits_in_window(
    chain: list[KnowledgeCommit],
    window: str,
    start_dt_str: Optional[str] = None,
    end_dt_str: Optional[str] = None
) -> list[KnowledgeCommit]:
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    if window == "today":
        start_time = today_start
        end_time = now + timedelta(days=1)
    elif window == "yesterday":
        start_time = today_start - timedelta(days=1)
        end_time = today_start
    elif window == "7d":
        start_time = now - timedelta(days=7)
        end_time = now + timedelta(days=1)
    elif window == "30d":
        start_time = now - timedelta(days=30)
        end_time = now + timedelta(days=1)
    elif window == "custom":
        start_time = _parse_iso(start_dt_str) or (now - timedelta(days=365))
        end_time = _parse_iso(end_dt_str) or (now + timedelta(days=1))
    else:  # "all"
        return list(chain)

    filtered = []
    for commit in chain:
        c_dt = _parse_iso(commit.created_at)
        if c_dt and start_time <= c_dt <= end_time:
            filtered.append(commit)
        elif not c_dt:
            # If no parsed dt, fall back to inclusion if "all" or recent
            filtered.append(commit)

    return filtered


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


def generate_daily_chronicle(
    store: KnowledgeStore,
    window: str = "today",
    start_dt_str: Optional[str] = None,
    end_dt_str: Optional[str] = None
) -> dict[str, Any]:
    """
    Pure deterministic report generator. 
    Never produces natural language narrative. Outputs pure structured facts, 
    diffs, and cryptographic snapshots.
    """
    chain = store.get_chain()
    filtered_commits = filter_commits_in_window(chain, window, start_dt_str, end_dt_str)

    new_decisions = []
    new_goals = []
    new_risks = []
    assumption_changes = {"new": [], "validated": [], "invalidated": [], "superseded": []}
    questions = {"new": [], "answered": [], "unresolved": []}
    action_items = {"new": [], "completed": [], "outstanding": []}
    principles = []

    distinct_paths = set()
    distinct_senders = set()
    distinct_rels = set()
    total_nodes = 0
    non_generic_nodes = 0

    knowledge_added = 0
    knowledge_updated = 0
    knowledge_superseded = 0
    knowledge_archived = 0
    knowledge_invalidated = 0

    for commit in filtered_commits:
        c_hash = commit.commit_hash
        c_ts = commit.created_at.isoformat() if hasattr(commit.created_at, "isoformat") else str(commit.created_at)

        for node in commit.kir_nodes:
            total_nodes += 1
            meta = node.metadata or {}
            c_dict = _extract_content(meta)

            st_type = str(meta.get("type", meta.get("semantic_type", "UNKNOWN"))).upper()
            if st_type != "UNKNOWN" and st_type != "OBSERVATION":
                non_generic_nodes += 1
                knowledge_added += 1

            sender = meta.get("sender", c_dict.get("sender", ""))
            if sender:
                distinct_senders.add(sender)
            src_path = meta.get("source_path", c_dict.get("source_path", ""))
            if src_path:
                distinct_paths.add(src_path)

            # Timeline navigation trace item
            trace_item = {
                "id": node.output_id,
                "commit_hash": c_hash,
                "timestamp": c_ts,
                "type": st_type,
                "title": c_dict.get("title", c_dict.get("description", c_dict.get("question", c_dict.get("statement", node.output_id)))),
                "supporting_artifact": src_path or c_dict.get("supporting_artifact", ""),
                "evidence_span": meta.get("evidence_span", c_dict.get("evidence_span", "")),
                "confidence": meta.get("confidence", c_dict.get("confidence", 0.9)),
                "content": c_dict
            }

            if st_type == "DECISION":
                new_decisions.append({
                    **trace_item,
                    "rationale": c_dict.get("rationale", c_dict.get("reasoning", "")),
                    "participants": c_dict.get("participants", [])
                })
            elif st_type == "GOAL":
                new_goals.append(trace_item)
            elif st_type == "RISK":
                new_risks.append({
                    **trace_item,
                    "severity": c_dict.get("severity", c_dict.get("impact", "medium")),
                    "supporting_evidence": c_dict.get("supporting_evidence", "")
                })
            elif st_type == "ASSUMPTION":
                status = str(c_dict.get("status", "assumption")).lower()
                if status in ["validated", "valid"]:
                    assumption_changes["validated"].append(trace_item)
                elif status in ["invalidated", "invalid", "false"]:
                    assumption_changes["invalidated"].append(trace_item)
                    knowledge_invalidated += 1
                elif status in ["superseded", "replaced"]:
                    assumption_changes["superseded"].append(trace_item)
                    knowledge_superseded += 1
                else:
                    assumption_changes["new"].append(trace_item)
            elif st_type == "QUESTION":
                status = str(c_dict.get("status", "unresolved")).lower()
                if status in ["answered", "resolved", "closed"]:
                    questions["answered"].append(trace_item)
                    knowledge_updated += 1
                else:
                    questions["new"].append(trace_item)
                    questions["unresolved"].append(trace_item)
            elif st_type == "ACTION_ITEM":
                status = str(c_dict.get("status", "open")).lower()
                if status in ["completed", "done", "closed"]:
                    action_items["completed"].append(trace_item)
                    knowledge_archived += 1
                else:
                    action_items["new"].append(trace_item)
                    action_items["outstanding"].append(trace_item)
            elif st_type == "PRINCIPLE":
                principles.append(trace_item)
            elif st_type == "RELATIONSHIP":
                distinct_rels.add(node.output_id)

    # Compute Chronicle Growth stats
    chronicle_growth = {
        "commits": len(filtered_commits),
        "artifacts_added": len(distinct_paths),
        "observations_added": total_nodes,
        "semantic_objects_added": non_generic_nodes,
        "new_entities": len(distinct_senders),
        "relationships": len(distinct_rels)
    }

    memory_evolution = {
        "knowledge_added": knowledge_added,
        "knowledge_updated": knowledge_updated,
        "knowledge_superseded": knowledge_superseded,
        "knowledge_archived": knowledge_archived,
        "knowledge_invalidated": knowledge_invalidated
    }

    commit_range = [c.commit_hash for c in filtered_commits] if filtered_commits else []
    range_bounds = [commit_range[0], commit_range[-1]] if len(commit_range) >= 2 else (commit_range * 2 if commit_range else ["none", "none"])

    # Deterministic JSON payload for hashing
    raw_report_dict = {
        "window": window,
        "commit_range": range_bounds,
        "new_decisions": new_decisions,
        "new_goals": new_goals,
        "new_risks": new_risks,
        "assumption_changes": assumption_changes,
        "questions": questions,
        "action_items": action_items,
        "principles": principles,
        "chronicle_growth": chronicle_growth,
        "memory_evolution": memory_evolution
    }
    
    # Surface Integrity alerts if snapshot is available
    integ = getattr(store, "integrity_snapshot", None)
    if integ:
        raw_report_dict["integrity_alerts"] = {
            "health_score": integ.get("health_score", 100),
            "lonely_knowledge": integ.get("lonely_knowledge", []),
            "contradictions": integ.get("contradictions", [])
        }

    report_json_str = json.dumps(raw_report_dict, sort_keys=True)
    report_hash = hashlib.sha256(report_json_str.encode("utf-8")).hexdigest()
    snapshot_id = f"snap_{report_hash[:12]}"

    snapshot = ChronicleSnapshot(
        snapshot_id=snapshot_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        window=window,
        commit_range=range_bounds,
        report_hash=report_hash
    )

    return {
        "snapshot": asdict(snapshot),
        **raw_report_dict
    }


def compute_knowledge_health(store: KnowledgeStore) -> dict[str, Any]:
    """
    Monitoring the health of the organizational knowledge base.
    Surfaces compiler-derived signals requiring review or refinement.
    """
    chain = store.get_chain()
    
    unresolved_questions = []
    open_risks = []
    unsupported_decisions = []
    weak_evidence = []
    stale_assumptions = []
    goals_without_progress = []
    action_items_without_owners = []
    unspecified_confidence = []

    now = datetime.now(timezone.utc)

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
                "type": st_type,
                "title": c_dict.get("title", c_dict.get("description", c_dict.get("question", c_dict.get("statement", node.output_id)))),
                "supporting_artifact": meta.get("source_path", c_dict.get("supporting_artifact", "")),
                "confidence": meta.get("confidence", c_dict.get("confidence")),
                "evidence_span": meta.get("evidence_span", c_dict.get("evidence_span", ""))
            }

            # 1. Weak Evidence signal
            conf = trace_item["confidence"]
            span = str(trace_item["evidence_span"]).strip()
            if conf is None:
                if st_type == "DECISION":
                    unspecified_confidence.append(trace_item)
            elif float(conf) < 0.85 or span in ["", "Header", "None", "Unknown", "none"]:
                weak_evidence.append({**trace_item, "health_reason": f"Low confidence ({float(conf):.2f}) or vague span '{span}'"})

            # 2. Unresolved Questions
            if st_type == "QUESTION" and str(c_dict.get("status", "unresolved")).lower() not in ["answered", "resolved", "closed"]:
                unresolved_questions.append(trace_item)

            # 3. Open Risks
            if st_type == "RISK" and str(c_dict.get("status", "open")).lower() not in ["mitigated", "resolved", "closed"]:
                open_risks.append(trace_item)

            # 4. Unsupported Decisions
            if st_type == "DECISION":
                supp_obs = c_dict.get("supporting_observations", [])
                supp_art = trace_item["supporting_artifact"]
                if not supp_obs and not supp_art:
                    unsupported_decisions.append({**trace_item, "health_reason": "Missing supporting observations or artifact citations"})

            # 5. Stale Assumptions (> 30 days)
            if st_type == "ASSUMPTION" and str(c_dict.get("status", "assumption")).lower() in ["assumption", "unvalidated"]:
                age_days = (now - c_dt).days
                if age_days >= 30:
                    stale_assumptions.append({**trace_item, "health_reason": f"Unvalidated for {age_days} days"})

            # 6. Goals Without Progress
            if st_type == "GOAL" and str(c_dict.get("status", "active")).lower() in ["active", "in_progress"]:
                prog = int(c_dict.get("progress", 0))
                if prog == 0:
                    goals_without_progress.append({**trace_item, "health_reason": "Progress is 0%"})

            # 7. Action Items Without Owners
            if st_type == "ACTION_ITEM" and str(c_dict.get("status", "open")).lower() not in ["completed", "done", "closed"]:
                owner = str(c_dict.get("owner", "unknown")).strip().lower()
                if owner in ["unknown", "none", "", "unassigned", "tbd"]:
                    action_items_without_owners.append({**trace_item, "health_reason": "No assigned owner"})

    # Compute overall health score (100 minus penalties)
    penalties = (
        len(unresolved_questions) * 3 +
        len(open_risks) * 5 +
        len(unsupported_decisions) * 8 +
        len(weak_evidence) * 2 +
        len(stale_assumptions) * 4 +
        len(goals_without_progress) * 3 +
        len(action_items_without_owners) * 3
    )
    health_score = max(0, min(100, 100 - penalties))

    if health_score >= 85: health_zone = "ROBUST"
    elif health_score >= 65: health_zone = "STABLE"
    elif health_score >= 45: health_zone = "DEGRADED"
    else: health_zone = "CRITICAL"

    return {
        "health_score": health_score,
        "health_zone": health_zone,
        "total_issues": (
            len(unresolved_questions) + len(open_risks) + len(unsupported_decisions) +
            len(weak_evidence) + len(stale_assumptions) + len(goals_without_progress) + len(action_items_without_owners)
        ),
        "unresolved_questions": unresolved_questions,
        "open_risks": open_risks,
        "unsupported_decisions": unsupported_decisions,
        "weak_evidence": weak_evidence,
        "stale_assumptions": stale_assumptions,
        "goals_without_progress": goals_without_progress,
        "action_items_without_owners": action_items_without_owners,
        "unspecified_confidence": unspecified_confidence
    }
