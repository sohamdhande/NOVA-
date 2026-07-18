from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from nova.packages.kir import KIRNode
from nova.packages.runtime import KnowledgeStore
import json

@dataclass(frozen=True)
class ResolvedNode:
    node: KIRNode
    status: str  # "ACTIVE", "SUPERSEDED", or "INVALIDATED"
    superseded_by: Optional[str]
    first_committed_at: datetime
    last_updated_at: datetime

@dataclass(frozen=True)
class StateSnapshot:
    buckets: dict[str, list[ResolvedNode]]
    generated_from_chain_length: int
    category_counts: dict[str, int]

@dataclass(frozen=True)
class AlternativeMatch:
    alternative: ResolvedNode
    match_confidence: str
    matched_on: str

def resolve_current_state(store: KnowledgeStore) -> dict[str, ResolvedNode]:
    """
    Walks the full commit chain and lineage edges once, and returns a mapping
    of output_id -> ResolvedNode, where each ResolvedNode carries:
      - the original KIRNode
      - a resolved `status` field: "ACTIVE", "SUPERSEDED", or "INVALIDATED"
      - `superseded_by`: Optional[str] — the output_id of the node that
        superseded/invalidated it, if any (via a SUPERSEDES or INVALIDATES
        lineage edge pointing TO this node's output_id as the "from")
      - `first_committed_at` / `last_updated_at` timestamps derived from the
        commit chain (created_at field of the KnowledgeCommit containing it)

    A node with no outgoing SUPERSEDES/INVALIDATES edge pointing away from it
    is ACTIVE. This function must not mutate anything — it is a pure read/
    projection function, consistent with the rest of Chronicle's deterministic
    design.
    """
    chain = store.get_chain()
    
    # Use get_lineage_edges if available (like in SQLiteCommitStore)
    if hasattr(store, "get_lineage_edges"):
        edges = store.get_lineage_edges()
    else:
        edges = []

    # Map to track state before freezing into ResolvedNode
    node_map = {}
    
    # 1. Process commit chain
    for commit in chain:
        for node in commit.kir_nodes:
            oid = node.output_id
            if oid not in node_map:
                node_map[oid] = {
                    "node": node,
                    "first_committed_at": commit.created_at,
                    "last_updated_at": commit.created_at,
                    "status": "ACTIVE",
                    "superseded_by": None
                }
            else:
                # Update last_updated_at and latest node instance
                node_map[oid]["last_updated_at"] = commit.created_at
                node_map[oid]["node"] = node
                
    # 2. Process lineage edges
    # Sort edges by created_at to apply them in chronological order
    edges_sorted = sorted(edges, key=lambda e: e.get("created_at", ""))
    
    for edge in edges_sorted:
        from_id = edge.get("from_id")
        to_id = edge.get("to_id")
        verb = edge.get("verb", "").upper()
        
        if from_id in node_map:
            if verb == "SUPERSEDES":
                node_map[from_id]["status"] = "SUPERSEDED"
                node_map[from_id]["superseded_by"] = to_id
            elif verb == "INVALIDATES":
                node_map[from_id]["status"] = "INVALIDATED"
                node_map[from_id]["superseded_by"] = to_id

    # 3. Build frozen dataclasses
    resolved = {}
    for oid, data in node_map.items():
        resolved[oid] = ResolvedNode(
            node=data["node"],
            status=data["status"],
            superseded_by=data["superseded_by"],
            first_committed_at=data["first_committed_at"],
            last_updated_at=data["last_updated_at"]
        )
        
    return resolved

def bucket_by_category(
    resolved: dict[str, ResolvedNode]
) -> dict[str, list[ResolvedNode]]:
    """
    Groups resolved nodes by their metadata["type"] category.
    Returns a dict keyed by the exact category string found in the data.
    Nodes with a missing or unrecognized metadata["type"] should be collected
    under a key "uncategorized" rather than dropped or raising an error.
    Within each category's list, sort deterministically by
    first_committed_at ascending (oldest first).
    """
    buckets = {}
    
    for resolved_node in resolved.values():
        cat = resolved_node.node.metadata.get("type")
        if not cat or not isinstance(cat, str):
            cat_key = "uncategorized"
        else:
            cat_key = cat
            
        if cat_key not in buckets:
            buckets[cat_key] = []
        buckets[cat_key].append(resolved_node)
        
    for cat_key in buckets:
        buckets[cat_key].sort(key=lambda r: r.first_committed_at)
        
    return buckets

def get_state_snapshot(store: KnowledgeStore) -> StateSnapshot:
    """
    The single entry point Master Report (and future consumers) should call.
    Combines resolve_current_state() + bucket_by_category() into one
    convenient, deterministic structure.
    """
    chain = store.get_chain()
    resolved = resolve_current_state(store)
    buckets = bucket_by_category(resolved)
    
    counts = {k: len(v) for k, v in buckets.items()}
    
    return StateSnapshot(
        buckets=buckets,
        generated_from_chain_length=len(chain),
        category_counts=counts
    )

def get_alternatives_for_decision(
    snapshot: StateSnapshot, decision_output_id: str
) -> list[AlternativeMatch]:
    """
    Returns ALTERNATIVE nodes linked to a specific DECISION node.
    Provides a match_confidence ("exact", "partial", "ambiguous") and 
    the matched_on string to guard against false-positive pairings.
    """
    import re
    
    decision_node = None
    for r in snapshot.buckets.get("DECISION", []):
        if r.node.output_id == decision_output_id:
            decision_node = r
            break
            
    if not decision_node:
        return []
        
    def get_dec_title(dec: ResolvedNode) -> str:
        content = dec.node.metadata.get("content", {})
        if isinstance(content, str):
            try: content = json.loads(content)
            except Exception: content = {}
        t = content.get("title", "").strip().lower()
        return re.sub(r'\s+', ' ', t)

    target_title = get_dec_title(decision_node)
    if not target_title:
        return []

    # Pre-parse all decision titles to check for ambiguous multi-matches
    all_decs = {}
    for r in snapshot.buckets.get("DECISION", []):
        t = get_dec_title(r)
        if t:
            all_decs[r.node.output_id] = t
            
    linked = []
    for alt in snapshot.buckets.get("ALTERNATIVE", []):
        alt_content = alt.node.metadata.get("content", {})
        if isinstance(alt_content, str):
            try: alt_content = json.loads(alt_content)
            except Exception: alt_content = {}
                
        chosen_raw = alt_content.get("chosen_option", "").strip().lower()
        chosen = re.sub(r'\s+', ' ', chosen_raw)
        
        if not chosen:
            continue
            
        # Find all decisions this alternative matches
        matched_dec_ids = []
        for dec_id, title in all_decs.items():
            if chosen in title or title in chosen:
                matched_dec_ids.append(dec_id)
                
        if decision_output_id in matched_dec_ids:
            if len(matched_dec_ids) > 1:
                confidence = "ambiguous"
            elif chosen == target_title:
                confidence = "exact"
            else:
                confidence = "partial"
                
            linked.append(AlternativeMatch(
                alternative=alt,
                match_confidence=confidence,
                matched_on=chosen
            ))
            
    return linked

def find_ambiguous_alternative_links(store: KnowledgeStore) -> list[AlternativeMatch]:
    """
    Scans all DECISION and ALTERNATIVE nodes in the current state snapshot
    and returns every match classified as 'ambiguous', so these can be
    surfaced to the user for manual review.
    """
    snapshot = get_state_snapshot(store)
    
    ambiguous = []
    seen_alt_ids = set()
    
    for dec in snapshot.buckets.get("DECISION", []):
        matches = get_alternatives_for_decision(snapshot, dec.node.output_id)
        for m in matches:
            if m.match_confidence == "ambiguous":
                if m.alternative.node.output_id not in seen_alt_ids:
                    ambiguous.append(m)
                    seen_alt_ids.add(m.alternative.node.output_id)
                    
    return ambiguous
