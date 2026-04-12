"""All Pydantic data models for the Project Predictive Analyzer."""

from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import date


# ── Raw parsed data ──────────────────────────────────────

class RiskRow(BaseModel):
    id: str
    impact: str
    probability: str
    severity: str          # resolved from Risk Chart
    status: str
    owner: str
    date_raised: Optional[date] = None
    date_closed: Optional[date] = None


class IssueRow(BaseModel):
    id: str
    priority: str
    root_cause: str
    status: str
    date_raised: Optional[date] = None
    date_due: Optional[date] = None
    date_resolved: Optional[date] = None


class MilestoneRow(BaseModel):
    name: str
    phase: str
    due_date: Optional[date] = None
    at_risk: bool
    status: str            # Achieved / Planned / Cancelled


class DependencyRow(BaseModel):
    id: str
    importance: str        # Very High / High / Medium
    due_date: Optional[date] = None
    date_completed: Optional[date] = None
    status: str


class AssumptionRow(BaseModel):
    id: str
    criticality: str
    validation_due: Optional[date] = None
    date_validated: Optional[date] = None
    validated: bool


class ActionItemRow(BaseModel):
    id: str
    owner: str
    due_date: Optional[date] = None
    date_completed: Optional[date] = None
    status: str


class KPIRow(BaseModel):
    month: str
    dimension: str         # e.g. "Excellence in Delivery"
    metric: str
    value: float


class RAMIDData(BaseModel):
    project_name: str = "Unknown"
    risks: list[RiskRow] = []
    issues: list[IssueRow] = []
    milestones: list[MilestoneRow] = []
    dependencies: list[DependencyRow] = []
    assumptions: list[AssumptionRow] = []
    action_items: list[ActionItemRow] = []
    kpi_rows: list[KPIRow] = []


# ── Config ───────────────────────────────────────────────

class ThresholdConfig(BaseModel):
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "time": 1 / 6,
            "cost": 1 / 6,
            "scope": 1 / 6,
            "people": 1 / 6,
            "dependencies": 1 / 6,
            "risks": 1 / 6,
        }
    )
    overdue_age_limit_days: int = 30
    assumption_staleness_days: int = 90
    team_overload_limit: int = 5

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "ThresholdConfig":
        total = sum(self.weights.values())
        assert abs(total - 1.0) < 1e-6, f"Weights must sum to 1.0, got {total}"
        return self


# ── Scoring output ───────────────────────────────────────

class ContributingFactor(BaseModel):
    dimension: str
    label: str             # e.g. "3 open High-severity risks"
    source_sheet: str
    row_reference: str


class DimensionScores(BaseModel):
    time: float
    cost: float
    scope: float
    people: float
    dependencies: float
    risks: float


class AnalysisResult(BaseModel):
    composite: int                              # 0–100
    rag_status: str                             # On Track / At Risk / Critical
    dimensions: DimensionScores
    contributing_factors: list[ContributingFactor] = []
    executive_summary: str = ""
    recommendations: list[str] = []
    project_name: str = "Unknown"
    generated_at: str = ""                      # ISO timestamp


# ── LLM structured output ────────────────────────────────

class LLMResponse(BaseModel):
    executive_summary: str
    recommendations: list[str] = Field(max_length=3)
