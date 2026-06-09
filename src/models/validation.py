from pydantic import BaseModel, computed_field

from .features import Entity
from .summary import CallSummary


class EntityMismatch(BaseModel):
    entity_type: str
    transcript_value: str
    summary_value: str
    severity: str  # "critical" | "minor"


class FactualCheck(BaseModel):
    transcript_id: str
    entities_in_transcript: list[Entity] = []
    entities_in_summary: list[Entity] = []
    hallucinated_entities: list[Entity] = []
    missing_critical_entities: list[Entity] = []
    mismatched_values: list[EntityMismatch] = []
    factual_score: float = 1.0


class QualityIssue(BaseModel):
    check: str
    severity: str  # "critical" | "warning" | "minor"
    description: str
    suggestion: str = ""


class QualityScore(BaseModel):
    transcript_id: str
    issue_and_actions_clear: float = 0.0
    critical_facts_accurate: float = 0.0
    handoff_ready: float = 0.0
    professional_tone: float = 0.0
    within_char_limit: bool = True
    overall_score: float = 0.0
    issues_found: list[QualityIssue] = []


class SummaryResult(BaseModel):
    transcript_id: str
    category: str
    summary: CallSummary
    rendered: str = ""
    structural_valid: bool = True
    factual_check: FactualCheck | None = None
    quality_score: QualityScore | None = None
    attempts: int = 1
    needs_human_review: bool = False

    @computed_field
    @property
    def confidence(self) -> float:
        factual = self.factual_check.factual_score if self.factual_check else 1.0
        quality = self.quality_score.overall_score if self.quality_score else 0.5
        structural = 1.0 if self.structural_valid else 0.0
        return factual * 0.5 + quality * 0.3 + structural * 0.2
