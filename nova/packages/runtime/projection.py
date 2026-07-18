from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from nova.packages.runtime.store import KnowledgeStore
from nova.packages.temporal import TemporalIndex

@dataclass(frozen=True)
class Projection:
    facts: list[dict[str, Any]]
    as_of: datetime

def project_current_state(store: KnowledgeStore, temporal_idx=None) -> Projection:
    """
    Lineage-aware projection: groups facts by lineage_id and returns the one 
    with the latest occurrence_time among those whose temporal intervals are still open.
    """
    now = datetime.now(timezone.utc)
    if temporal_idx is None:
        try:
            import os
            from nova.packages.temporal.persistence import SQLiteTemporalIndex
            if hasattr(store, 'db_path') and store.db_path:
                temp_path = os.path.join(os.path.dirname(store.db_path), "temporal.db")
                if os.path.exists(temp_path):
                    temporal_idx = SQLiteTemporalIndex(temp_path)
            if temporal_idx is None:
                from nova.packages.cli.main import get_temporal
                temporal_idx = get_temporal()
        except Exception as e:
            print("EXCEPTION IN project_current_state:", e)
            temporal_idx = None
            
    valid_ids = set(temporal_idx.valid_facts_as_of(now)) if temporal_idx else None

    lineage_map = {}
    isolated_facts = []

    for commit in store.get_chain():
        for node in commit.kir_nodes:
            raw_id = node.output_id
            fact_id = raw_id[4:] if raw_id.startswith("kir_") else raw_id
            
            print(f"DEBUG: Checking {raw_id} (fact_id: {fact_id}). valid_ids={valid_ids}")
            if valid_ids is not None and fact_id not in valid_ids and raw_id not in valid_ids:
                print(f"DEBUG: Skipping {raw_id} - not in valid_ids")
                continue
                
            lin_info = getattr(store, "get_node_lineage", lambda x: None)(raw_id)
            if not lin_info:
                lin_info = getattr(store, "get_node_lineage", lambda x: None)(fact_id)
                
            print(f"DEBUG: Lineage info for {raw_id}: {lin_info}")
            if lin_info:
                lin_id = lin_info["lineage_id"]
                occ_time = lin_info["occurrence_time"]
                
                if lin_id not in lineage_map:
                    lineage_map[lin_id] = (node.metadata, occ_time)
                else:
                    if occ_time > lineage_map[lin_id][1]:
                        lineage_map[lin_id] = (node.metadata, occ_time)
            else:
                isolated_facts.append(node.metadata)

    facts = isolated_facts + [v[0] for v in lineage_map.values()]
    return Projection(
        facts=facts,
        as_of=now
    )

def reconstruct_as_of(store: KnowledgeStore, index: TemporalIndex, as_of: datetime) -> Projection:
    valid_ids = set(index.valid_facts_as_of(as_of))
    
    lineage_map = {}
    isolated_facts = []
    
    for commit in store.get_chain():
        for node in commit.kir_nodes:
            raw_id = node.output_id
            fact_id = raw_id[4:] if raw_id.startswith("kir_") else raw_id
            
            if fact_id in valid_ids or raw_id in valid_ids:
                lin_info = getattr(store, "get_node_lineage", lambda x: None)(raw_id)
                if not lin_info:
                    lin_info = getattr(store, "get_node_lineage", lambda x: None)(fact_id)
                    
                if lin_info:
                    lin_id = lin_info["lineage_id"]
                    occ_time = lin_info["occurrence_time"]
                    
                    if lin_id not in lineage_map:
                        lineage_map[lin_id] = (node.metadata, occ_time)
                    else:
                        if occ_time > lineage_map[lin_id][1]:
                            lineage_map[lin_id] = (node.metadata, occ_time)
                else:
                    isolated_facts.append(node.metadata)
                
    facts = isolated_facts + [v[0] for v in lineage_map.values()]
    return Projection(
        facts=facts,
        as_of=as_of
    )
