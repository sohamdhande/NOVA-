from dataclasses import dataclass, field
from typing import Optional
import uuid

class SuggestionAlreadyDecidedError(Exception):
    pass

class SuggestionAlreadyRejectedError(SuggestionAlreadyDecidedError):
    pass

class AIIsolationViolationError(Exception):
    pass

@dataclass(frozen=True)
class Suggestion:
    suggestion_type: str
    payload: dict
    confidence: float
    source: str
    suggestion_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    originating_model: Optional[str] = None
    originating_prompt: Optional[str] = None
    explanation: Optional[str] = None
    evidence_span: Optional[str] = None
    parser_reference: Optional[str] = None
