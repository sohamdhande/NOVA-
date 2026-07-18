from typing import List
from .models import Suggestion, SuggestionAlreadyDecidedError, SuggestionAlreadyRejectedError, AIIsolationViolationError
import logging

logger = logging.getLogger(__name__)
class SuggestionReviewBoundary:
    def __init__(self):
        self._pending: List[Suggestion] = []
        self._decided: set[int] = set() # Store id(suggestion) for simplicity
        self._rejected: set[int] = set()

    def submit(self, suggestion: Suggestion) -> None:
        forbidden_keys = {"commit_hash", "kir_nodes", "identity_override", "knowledge_commit"}
        if any(k in suggestion.payload for k in forbidden_keys):
            raise AIIsolationViolationError(f"Suggestion payload contains forbidden authority keys: {forbidden_keys & suggestion.payload.keys()}")
        self._pending.append(suggestion)

    def pending(self) -> List[Suggestion]:
        return list(self._pending)

    def accept(self, suggestion: Suggestion, accepted_by: str) -> dict:
        sid = id(suggestion)
        if sid in self._rejected:
            raise SuggestionAlreadyRejectedError("This suggestion was already rejected.")
        if sid in self._decided:
            raise SuggestionAlreadyDecidedError("This suggestion was already accepted.")
            
        self._decided.add(sid)
        if suggestion in self._pending:
            self._pending.remove(suggestion)
            
        payload = dict(suggestion.payload)
        payload["_accepted_by"] = accepted_by
        return payload

    def reject(self, suggestion: Suggestion, reason: str) -> None:
        sid = id(suggestion)
        if sid in self._decided and sid not in self._rejected:
            raise SuggestionAlreadyDecidedError("This suggestion was already accepted.")
        if sid in self._rejected:
            raise SuggestionAlreadyRejectedError("This suggestion was already rejected.")
            
        self._decided.add(sid)
        self._rejected.add(sid)
        if suggestion in self._pending:
            self._pending.remove(suggestion)
        logger.info(f"[SuggestionReviewBoundary] Rejected suggestion from {suggestion.source}: {reason}")
