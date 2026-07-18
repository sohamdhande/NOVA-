from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from nova.packages.runtime.store import KnowledgeStore
from nova.packages.runtime.projection import Projection, project_current_state

@dataclass(frozen=True)
class DependencyEdge:
    projection_id: str
    depends_on_fact_id: str

class DependencyGraph:
    def __init__(self):
        # Maps projection_id -> list[fact_id]
        self._proj_to_facts: dict[str, list[str]] = {}
        # Maps fact_id -> list[projection_id]
        self._fact_to_projs: dict[str, list[str]] = {}

    def record_dependency(self, projection_id: str, fact_id: str) -> None:
        self._proj_to_facts.setdefault(projection_id, []).append(fact_id)
        self._fact_to_projs.setdefault(fact_id, []).append(projection_id)

    def get_dependencies(self, projection_id: str) -> list[str]:
        return self._proj_to_facts.get(projection_id, [])

    def get_dependents(self, fact_id: str) -> list[str]:
        return self._fact_to_projs.get(fact_id, [])

    def invalidate(self, fact_id: str) -> list[str]:
        """
        Returns the list of projection_ids that are now stale because fact_id changed.
        Does not actually recompute them.
        """
        return self.get_dependents(fact_id)

@dataclass(frozen=True)
class TrackedProjection:
    projection_id: str
    facts: list[dict[str, Any]]
    as_of: datetime
    computed_at: datetime
    is_stale: bool

def compute_tracked_projection(store: KnowledgeStore, graph: DependencyGraph, projection_id: str) -> TrackedProjection:
    proj = project_current_state(store)
    
    # Record a dependency edge for every fact_id that ended up in the projection
    # Since project_current_state includes everything currently in the chain:
    for commit in store.get_chain():
        for node in commit.kir_nodes:
            fact_id = node.output_id[4:] if node.output_id.startswith("kir_") else node.output_id
            graph.record_dependency(projection_id, fact_id)
            
    return TrackedProjection(
        projection_id=projection_id,
        facts=proj.facts,
        as_of=proj.as_of,
        computed_at=datetime.now(timezone.utc),
        is_stale=False
    )
