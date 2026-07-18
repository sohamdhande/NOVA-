from enum import Enum
from dataclasses import dataclass

class SemanticType(Enum):
    ARTIFACT = "ARTIFACT"
    ENTITY = "ENTITY"
    OBSERVATION = "OBSERVATION"
    ASSERTION = "ASSERTION"
    RELATIONSHIP = "RELATIONSHIP"
    EVENT = "EVENT"
    FACT = "FACT"
    EVIDENCE = "EVIDENCE"
    PROVENANCE = "PROVENANCE"
    DECISION = "DECISION"
    ASSUMPTION = "ASSUMPTION"
    HYPOTHESIS = "HYPOTHESIS"
    EXPERIMENT = "EXPERIMENT"
    RISK = "RISK"
    GOAL = "GOAL"
    METRIC = "METRIC"
    TASK = "TASK"
    CHANGE = "CHANGE"
    OUTCOME = "OUTCOME"
    CONSTRAINT = "CONSTRAINT"
    TRADEOFF = "TRADEOFF"
    ALTERNATIVE = "ALTERNATIVE"
    QUESTION = "QUESTION"
    ACTION_ITEM = "ACTION_ITEM"
    PRINCIPLE = "PRINCIPLE"
    MARKET_DATA = "MARKET_DATA"
    COMPETITOR = "COMPETITOR"
    TEAM_MEMBER = "TEAM_MEMBER"
    FINANCIAL_METRIC = "FINANCIAL_METRIC"

@dataclass(frozen=True)
class OntologyObject:
    id: str
    type: SemanticType
    attributes: dict

__all__ = [
    "SemanticType",
    "OntologyObject"
]
