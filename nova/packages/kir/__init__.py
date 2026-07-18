from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum
from nova.packages.ontology import SemanticType
from nova.packages.observation import Observation

class Dialect(Enum):
    COMMUNICATION = "COMMUNICATION"
    CODE_CHANGE = "CODE_CHANGE"
    DECISION = "DECISION"
    GENERIC = "GENERIC"

@dataclass(frozen=True)
class KIRNode:
    op: str
    inputs: list[str]
    output_id: str
    metadata: dict[str, Any]
    dialect: Dialect = Dialect.GENERIC
    verification_status: str = "unverified"
    verified_at: Optional[str] = None

def classify_dialect(observation: Observation) -> Dialect:
    if observation.type == SemanticType.DECISION:
        return Dialect.DECISION
        
    content = observation.content
    
    # 1. Simple structural matching for raw dicts
    if "channel" in content or "thread_ts" in content:
        return Dialect.COMMUNICATION
    if "sha" in content or "commit" in content or "diff" in content:
        return Dialect.CODE_CHANGE
        
    # 2. Structural matching for adapter outputs
    source_path = content.get("source_path", "")
    if source_path.startswith("slack/"):
        return Dialect.COMMUNICATION
    if source_path.startswith("git/"):
        return Dialect.CODE_CHANGE
            
    return Dialect.GENERIC

def lower_to_kir(observation: Observation) -> KIRNode:
    dialect = classify_dialect(observation)
    
    op = "OBSERVE"
    
    if dialect == Dialect.COMMUNICATION:
        content = observation.content
        if "thread_ts" in content or content.get("source_path", "").endswith("/thread"):
            op = "THREAD_REPLY"
        else:
            op = "MESSAGE_SENT"
    elif dialect == Dialect.CODE_CHANGE:
        content = observation.content
        if "diff" in content or content.get("source_path", "").startswith("git/diff"):
            op = "DIFF_APPLIED"
        else:
            op = "COMMIT"
    elif dialect == Dialect.DECISION:
        op = "DECISION_MADE"
        
    return KIRNode(
        op=op,
        inputs=[],
        output_id=f"kir_{observation.id}",
        metadata={
            "type": observation.type.value,
            "content": observation.content,
            "identity": observation.identity
        },
        dialect=dialect
    )

__all__ = [
    "Dialect",
    "KIRNode",
    "classify_dialect",
    "lower_to_kir"
]
