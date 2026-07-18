import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

class IdentityMergeError(Exception):
    pass

class UnknownAliasError(Exception):
    pass

@dataclass(frozen=True)
class Entity:
    canonical_id: str
    known_aliases: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    merged_into: Optional[str] = None

class IdentityRegistry:
    def __init__(self):
        self._entities: dict[str, Entity] = {}
        self._alias_index: dict[str, str] = {}
        self._merges: list[tuple[str, str]] = []
        
    def resolve(self, raw_object: dict, alias_key: str) -> str:
        alias = raw_object.get(alias_key)
        if alias is None:
            # If alias_key is completely missing, we might use string representation as the alias.
            # But normally we'd expect the alias to exist.
            alias = str(raw_object)
            
        canonical_id = self._alias_index.get(alias)
        if canonical_id is not None:
            entity = self.get_entity(canonical_id)
            return entity.canonical_id
            
        new_id = str(uuid.uuid4())
        new_entity = Entity(
            canonical_id=new_id,
            known_aliases=[alias]
        )
        self._entities[new_id] = new_entity
        self._alias_index[alias] = new_id
        return new_id
        
    def add_alias(self, canonical_id: str, new_alias: str) -> None:
        entity = self.get_entity(canonical_id)
        if new_alias not in entity.known_aliases:
            updated_aliases = list(entity.known_aliases) + [new_alias]
            new_entity = Entity(
                canonical_id=entity.canonical_id,
                known_aliases=updated_aliases,
                created_at=entity.created_at,
                merged_into=entity.merged_into
            )
            self._entities[entity.canonical_id] = new_entity
            self._alias_index[new_alias] = entity.canonical_id
            
    def get_entity(self, canonical_id: str) -> Entity:
        if canonical_id not in self._entities:
            raise ValueError(f"Unknown canonical_id: {canonical_id}")
            
        current = self._entities[canonical_id]
        visited = set()
        while current.merged_into is not None:
            if current.canonical_id in visited:
                raise IdentityMergeError("Merge cycle detected while walking entity chain.")
            visited.add(current.canonical_id)
            current = self._entities[current.merged_into]
            
        # Final cycle check on the last node
        if current.canonical_id in visited:
            raise IdentityMergeError("Merge cycle detected while walking entity chain.")
            
        return current
        
    def merge(self, source_id: str, target_id: str) -> None:
        if source_id not in self._entities:
            raise IdentityMergeError(f"Source {source_id} not found.")
        if target_id not in self._entities:
            raise IdentityMergeError(f"Target {target_id} not found.")
            
        source = self.get_entity(source_id)
        target = self.get_entity(target_id)
        
        if source.canonical_id == target.canonical_id:
            raise IdentityMergeError("Cannot merge entity into itself.")
            
        # Update source as tombstone
        updated_source = Entity(
            canonical_id=source.canonical_id,
            known_aliases=source.known_aliases,
            created_at=source.created_at,
            merged_into=target.canonical_id
        )
        self._entities[source.canonical_id] = updated_source
        
        # Detect cycle
        try:
            self.get_entity(source_id)
        except IdentityMergeError:
            # Rollback
            self._entities[source.canonical_id] = source
            raise
            
        # Transfer aliases to target
        new_aliases = sorted(list(set(target.known_aliases + source.known_aliases)))
        updated_target = Entity(
            canonical_id=target.canonical_id,
            known_aliases=new_aliases,
            created_at=target.created_at,
            merged_into=target.merged_into
        )
        self._entities[target.canonical_id] = updated_target
        
        for alias in source.known_aliases:
            self._alias_index[alias] = target.canonical_id
            
        self._merges.append((source.canonical_id, target.canonical_id))
        
    def history(self, canonical_id: str) -> list[str]:
        final_id = self.get_entity(canonical_id).canonical_id
        result = []
        for src, tgt in self._merges:
            if self.get_entity(tgt).canonical_id == final_id:
                result.append(src)
        return result

    def lookup_by_alias(self, alias: str) -> Optional[str]:
        cid = self._alias_index.get(alias)
        if not cid:
            return None
        return self.get_entity(cid).canonical_id


__all__ = [
    "Entity",
    "IdentityRegistry",
    "IdentityMergeError",
    "UnknownAliasError"
]
