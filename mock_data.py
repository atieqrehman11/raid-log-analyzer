"""Hardcoded AnalysisResult for UI development and testing."""

from datetime import datetime
from core.models import AnalysisResult, DimensionScores, ContributingFactor

MOCK_RESULT = AnalysisResult(
    composite=58,
    rag_status="At Risk",
    dimensions=DimensionScores(
        time=45,
        cost=62,
        scope=55,
        people=70,
        dependencies=48,
        risks=52,
    ),
    contributing_factors=[
        ContributingFactor(
            dimension="Risks",
            label="3 open High-severity risks",
            source_sheet="Risks",
            row_reference="R-004, R-007, R-012",
        ),
        ContributingFactor(
            dimension="Time",
            label="2 overdue milestones",
            source_sheet="Milestones",
            row_reference="M-003 (Phase 2 UAT), M-005 (Go-Live Prep)",
        ),
        ContributingFactor(
            dimension="People",
            label="Owner PM2 has 6 open action items",
            source_sheet="Action Items",
            row_reference="AI-011, AI-014, AI-017, AI-019, AI-022, AI-025",
        ),
    ],
    executive_summary=(
        "RAMID Demo Project is currently rated At Risk with a Composite Health Score of 58/100. "
        "The project faces significant headwinds across the Time and Dependencies dimensions, "
        "driven by two overdue milestones in Phase 2 and three unresolved high-severity risks "
        "that have remained open beyond the 30-day threshold. The People dimension is the "
        "strongest performer at 70, though workload concentration on PM2 warrants attention. "
        "Cost tracking is broadly on target at 62, but scope creep indicators from the Issues "
        "sheet suggest emerging pressure on delivery boundaries. Immediate focus should be "
        "directed at the overdue milestones and the high-severity risk backlog to prevent "
        "further score deterioration into Critical territory."
    ),
    recommendations=[
        "Escalate the three open High-severity risks (R-004, R-007, R-012) to the steering "
        "committee this week and assign dedicated owners with resolution deadlines within 14 days.",
        "Conduct an emergency milestone review for M-003 and M-005 to assess whether revised "
        "dates are achievable or whether a formal schedule re-baseline is required.",
        "Redistribute PM2's six open action items across available team members to reduce "
        "single-owner overload and improve the overall action item completion rate.",
    ],
    project_name="RAMID Demo Project",
    generated_at=datetime.now().isoformat(),
)
