from pydantic import BaseModel, Field
from typing import Optional, Any


class EntitySuggestion(BaseModel):
    id: str = Field(..., description="Normalized entity identifier")
    name: str = Field(..., description="Display name of the entity")
    type: str = Field("Unknown", description="Ontological category")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class RelationshipSuggestion(BaseModel):
    source: str = Field(..., description="Source entity ID")
    target: str = Field(..., description="Target entity ID")
    relation: str = Field(..., description="Relationship verb/type")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class ObservationSuggestion(BaseModel):
    content: str = Field(..., description="KIR observation text content")
    type: str = Field("ARTIFACT", description="Semantic type")
    dialect: str = Field("KNOWLEDGE", description="KIR dialect")
    op: str = Field("ASSERT", description="KIR operation")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


# Backward compatibility aliases
ExtractionEntity = EntitySuggestion
ExtractionRelationship = RelationshipSuggestion
ExtractionObservation = ObservationSuggestion


class DecisionSuggestion(BaseModel):
    title: str = Field(..., description="Decision title")
    summary: str = Field(..., description="Decision summary")
    rationale: str = Field("", description="Rationale behind decision")
    participants: list[str] = Field(default_factory=list)
    timestamp: str = Field("")
    supporting_observations: list[str] = Field(default_factory=list)
    decision_category: Optional[str] = Field(None, description="Category of the decision e.g. pricing, architecture, hiring")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class AssumptionSuggestion(BaseModel):
    description: str = Field(..., description="Assumption statement")
    status: str = Field("assumption")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class ConstraintSuggestion(BaseModel):
    description: str = Field(..., description="Constraint statement")
    scope: str = Field("Technical", description="Budget, Performance, Security, Compliance, Architecture, Timeline, Operational, Technical")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class RiskSuggestion(BaseModel):
    description: str = Field(..., description="Risk statement")
    category: str = Field("Technical", description="Technical, Business, Operational, Architecture, Security, Deployment")
    probability: str = Field("medium", description="AI estimate of probability")
    impact: str = Field("medium", description="AI estimate of impact")
    supporting_evidence: str = Field("")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class AlternativeSuggestion(BaseModel):
    topic: str = Field(..., description="Discussion topic comparing options")
    options: list[str] = Field(default_factory=list)
    chosen_option: str = Field("")
    rejected_options: list[str] = Field(default_factory=list)
    reasoning: str = Field("")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class TradeoffSuggestion(BaseModel):
    side_a: str = Field(..., description="One side of trade-off e.g. Performance")
    side_b: str = Field(..., description="Other side of trade-off e.g. Cost")
    description: str = Field("")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class GoalSuggestion(BaseModel):
    description: str = Field(..., description="Organizational goal")
    status: str = Field("active")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class ActionItemSuggestion(BaseModel):
    description: str = Field(..., description="Actionable work item")
    owner: str = Field("unknown")
    status: str = Field("open")
    supporting_artifact: str = Field("")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class QuestionSuggestion(BaseModel):
    question: str = Field(..., description="Unresolved question")
    status: str = Field("unresolved")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class PrincipleSuggestion(BaseModel):
    statement: str = Field(..., description="Long-lived engineering principle")
    rationale: str = Field("")
    is_foundational: bool = Field(False, description="Whether this is a core mission/vision principle vs routine")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class GeneralNoteSuggestion(BaseModel):
    content: str = Field(..., description="General note or reflection that does not fit other categories")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class MarketDataSuggestion(BaseModel):
    metric: str = Field(..., description="TAM, SAM, SOM")
    value: float = Field(...)
    unit: str = Field("USD")
    methodology: str = Field("", description="bottom_up, top_down")
    basis: str = Field("", description="string explaining the calculation")
    as_of_date: str = Field("", description="ISO date string")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class CompetitorSuggestion(BaseModel):
    name: str = Field(..., description="Competitor name")
    category: str = Field("direct", description="direct or indirect")
    strength: str = Field("")
    weakness: str = Field("")
    positioning_note: str = Field("")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class TeamMemberSuggestion(BaseModel):
    name: str = Field(...)
    role: str = Field(...)
    domain_expertise: str = Field("")
    prior_exits: str = Field("", description="empty string if none")
    is_founder: bool = Field(False)
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class FinancialMetricSuggestion(BaseModel):
    metric_type: str = Field(..., description="burn_rate, runway_months, ask_amount, cac, ltv, arr")
    value: float = Field(...)
    unit: str = Field("", description="USD, months, ratio")
    as_of_date: str = Field("", description="ISO date string")
    instrument: str = Field("", description="SAFE, priced_equity, empty string if none")
    evidence_span: str = Field("", description="Exact sentence or line range producing this suggestion")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_source: str = Field('live', description='Source of extraction: live or mock')


class StructuredExtractionResult(BaseModel):
    entities: list[EntitySuggestion] = Field(default_factory=list)
    relationships: list[RelationshipSuggestion] = Field(default_factory=list)
    observations: list[ObservationSuggestion] = Field(default_factory=list)
    decisions: list[DecisionSuggestion] = Field(default_factory=list)
    assumptions: list[AssumptionSuggestion] = Field(default_factory=list)
    constraints: list[ConstraintSuggestion] = Field(default_factory=list)
    risks: list[RiskSuggestion] = Field(default_factory=list)
    alternatives: list[AlternativeSuggestion] = Field(default_factory=list)
    tradeoffs: list[TradeoffSuggestion] = Field(default_factory=list)
    goals: list[GoalSuggestion] = Field(default_factory=list)
    action_items: list[ActionItemSuggestion] = Field(default_factory=list)
    questions: list[QuestionSuggestion] = Field(default_factory=list)
    principles: list[PrincipleSuggestion] = Field(default_factory=list)
    notes: list[GeneralNoteSuggestion] = Field(default_factory=list)
    market_data: list[MarketDataSuggestion] = Field(default_factory=list)
    competitors: list[CompetitorSuggestion] = Field(default_factory=list)
    team_members: list[TeamMemberSuggestion] = Field(default_factory=list)
    financial_metrics: list[FinancialMetricSuggestion] = Field(default_factory=list)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    reasoning: str = Field("", description="Explainability rationale for extraction")
