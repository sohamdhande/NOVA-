from dataclasses import dataclass, field

class ProvenanceCycleError(Exception):
    pass

@dataclass(frozen=True)
class ProvenanceLink:
    from_fact_id: str
    to_fact_id: str
    relation: str

@dataclass(frozen=True)
class ProvenanceChain:
    source: str
    derived_from: list[str]

class ProvenanceGraph:
    def __init__(self):
        self._forward: dict[str, list[ProvenanceLink]] = {}
        self._backward: dict[str, list[ProvenanceLink]] = {}
        
    def add_link(self, link: ProvenanceLink) -> None:
        if self._is_reachable(start_id=link.to_fact_id, target_id=link.from_fact_id, direction="forward"):
            raise ProvenanceCycleError(f"Adding link {link} creates a cycle.")
            
        self._forward.setdefault(link.from_fact_id, []).append(link)
        self._backward.setdefault(link.to_fact_id, []).append(link)
        
    def _is_reachable(self, start_id: str, target_id: str, direction: str) -> bool:
        if start_id == target_id:
            return True
            
        visited = set()
        queue = [start_id]
        
        while queue:
            current = queue.pop(0)
            if current == target_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            
            links = self._forward.get(current, []) if direction == "forward" else self._backward.get(current, [])
            next_nodes = [l.to_fact_id if direction == "forward" else l.from_fact_id for l in links]
            
            for n in next_nodes:
                if n not in visited:
                    queue.append(n)
                    
        return False

    def walk_backward(self, fact_id: str) -> list[ProvenanceLink]:
        links_found = []
        visited_nodes = set([fact_id])
        queue = [fact_id]
        
        while queue:
            current = queue.pop(0)
            back_links = self._backward.get(current, [])
            for link in back_links:
                if link not in links_found:
                    links_found.append(link)
                if link.from_fact_id not in visited_nodes:
                    visited_nodes.add(link.from_fact_id)
                    queue.append(link.from_fact_id)
                    
        links_found.reverse()
        return links_found
        
    def walk_forward(self, fact_id: str) -> list[ProvenanceLink]:
        links_found = []
        visited_nodes = set([fact_id])
        queue = [fact_id]
        
        while queue:
            current = queue.pop(0)
            fwd_links = self._forward.get(current, [])
            for link in fwd_links:
                if link not in links_found:
                    links_found.append(link)
                if link.to_fact_id not in visited_nodes:
                    visited_nodes.add(link.to_fact_id)
                    queue.append(link.to_fact_id)
                    
        return links_found
        
    def explain(self, fact_id: str) -> str:
        backward_links = self.walk_backward(fact_id)
        if not backward_links:
            return fact_id
            
        # Linearize for simple chains, or just list relations.
        # We will build a list of transitions.
        # E.g. "Decision -> [produced] -> Meeting"
        lines = []
        for link in backward_links:
            lines.append(f"{link.from_fact_id} --[{link.relation}]--> {link.to_fact_id}")
            
        return "\n".join(lines)


__all__ = [
    "ProvenanceCycleError",
    "ProvenanceLink",
    "ProvenanceChain",
    "ProvenanceGraph"
]
