from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from nova.packages.ontology import SemanticType
from nova.packages.temporal import TemporalRecord
from nova.packages.provenance import ProvenanceChain

@dataclass(frozen=True)
class Observation:
    id: str
    type: SemanticType
    content: dict[str, Any]
    identity: str
    temporal: TemporalRecord
    provenance: ProvenanceChain

@dataclass(frozen=True)
class ObservationBundle:
    id: str
    observations: list[Observation]
    created_at: datetime

from nova.packages.identity import IdentityRegistry
from nova.packages.temporal import TemporalIndex
from nova.packages.provenance import ProvenanceGraph, ProvenanceLink

def build_bundle(
    raw_artifact: dict[str, Any], 
    registry: IdentityRegistry, 
    temporal_index: TemporalIndex,
    provenance_graph: ProvenanceGraph,
    derived_from_ids: list[tuple[str, str]] = None,
    semantic_type_override: SemanticType = None,
    ai_suggestions: list[dict] = None
) -> ObservationBundle:
    if ai_suggestions:
        # Minimal integration point for AI suggestions.
        raw_artifact = dict(raw_artifact)
        raw_artifact["_ai_suggestions"] = ai_suggestions
        
    identity_hash = registry.resolve(raw_artifact, alias_key="sender")
    
    temporal_record = TemporalRecord()
    obs_id = f"obs_{identity_hash}"
    
    derived_ids = []
    if derived_from_ids:
        for parent_id, relation in derived_from_ids:
            if parent_id != obs_id:
                link = ProvenanceLink(from_fact_id=parent_id, to_fact_id=obs_id, relation=relation)
                provenance_graph.add_link(link)
                derived_ids.append(parent_id)
            
    obs_type = semantic_type_override if semantic_type_override else SemanticType.ARTIFACT
    
    obs = Observation(
        id=obs_id,
        type=obs_type,
        content=raw_artifact,
        identity=identity_hash,
        temporal=temporal_record,
        provenance=ProvenanceChain(source="build_bundle", derived_from=derived_ids)
    )
    
    temporal_index.register(obs_id, temporal_record)
    
    return ObservationBundle(
        id=f"bundle_{identity_hash}",
        observations=[obs],
        created_at=datetime.now(timezone.utc)
    )

def build_multi_bundle(
    items: list[dict[str, Any]],
    registry: IdentityRegistry,
    temporal_index: TemporalIndex,
    provenance_graph: ProvenanceGraph
) -> ObservationBundle:
    if not items:
        return ObservationBundle(id="bundle_empty", observations=[], created_at=datetime.now(timezone.utc))
        
    obs_list = []
    bundle_id_part = "multi"
    
    for idx, item in enumerate(items):
        raw_content = item.get("content", item)
        st_name = item.get("type", "OBSERVATION").upper()
        try:
            obs_type = SemanticType[st_name]
        except KeyError:
            obs_type = SemanticType.OBSERVATION
            
        content_dict = raw_content if isinstance(raw_content, dict) else {"content": str(raw_content)}
        identity_hash = registry.resolve(content_dict, alias_key="sender")
        if idx == 0:
            bundle_id_part = identity_hash
            
        temporal_record = TemporalRecord()
        obs_id = item.get("id", f"obs_{identity_hash}_{idx}")
        if not obs_id.startswith("obs_") and not obs_id.startswith("kir_"):
            obs_id = f"obs_{obs_id}"
            
        obs = Observation(
            id=obs_id,
            type=obs_type,
            content=content_dict,
            identity=identity_hash,
            temporal=temporal_record,
            provenance=ProvenanceChain(source="build_multi_bundle", derived_from=[])
        )
        temporal_index.register(obs_id, temporal_record)
        obs_list.append(obs)
        
    return ObservationBundle(
        id=f"bundle_{bundle_id_part}",
        observations=obs_list,
        created_at=datetime.now(timezone.utc)
    )

__all__ = [
    "Observation",
    "ObservationBundle",
    "build_bundle",
    "build_multi_bundle"
]
