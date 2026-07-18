from typing import Optional, Callable
import dataclasses
from nova.packages.compiler import KnowledgeCommit
from nova.packages.runtime.subscriptions import SubscriptionCallback

class ChainIntegrityError(Exception):
    pass

class KnowledgeStore:
    def __init__(self):
        self._history: list[KnowledgeCommit] = []
        self._subscriptions: list[SubscriptionCallback] = []
        
    def subscribe(self, callback: SubscriptionCallback):
        self._subscriptions.append(callback)
        
    def commit(self, kc: KnowledgeCommit):
        latest = self.get_latest()
        latest_hash = latest.commit_hash if latest else None
        
        # Automatically inject parent_hash
        kc = dataclasses.replace(kc, parent_hash=latest_hash)
        
        self._history.append(kc)
        
        # Event propagation
        for sub in self._subscriptions:
            sub(kc)
            
    def get_latest(self) -> Optional[KnowledgeCommit]:
        if not self._history:
            return None
        return self._history[-1]
        
    def get_chain(self) -> list[KnowledgeCommit]:
        expected_parent = None
        for commit in self._history:
            if commit.parent_hash != expected_parent:
                raise ChainIntegrityError(f"Broken link: expected parent {expected_parent}, got {commit.parent_hash}")
            expected_parent = commit.commit_hash
        return list(self._history)
