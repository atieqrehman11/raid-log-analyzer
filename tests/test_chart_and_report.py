"""Unit tests for ui/chart.py and ui/report.py."""

import pytest
import plotly.graph_objects as go

from core.models import AnalysisResult, DimensionScores, ContributingFactor
from mock_data import MOCK_RESULT
from ui.chart import build_radar, _DIMENSIONS
from ui.report import generate_html, ReportError


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_result(**overrides) -> AnalysisResult:
    """Return a copy of MOCK_RESULT with optional field overrides."""
    data = MOCK_RESULT.model_dump()
    data.update(overrides)
    return AnalysisResult(**data)


# ── chart.py tests ───────────────────────────────────────────────────────────

class TestBuildRadar:
    def test_returns_figure(self):
        fig = build_radar(MOCK_RESULT)
        assert isinstance(fig, go.Figure)

    def test_has_six_theta_labels(self):
        fig = build_radar(MOCK_RESULT)
        # The last trace is the data trace; its theta should contain all six labels
        data_trace = fig.data[-1]
        # theta is closed (first label repeated), so unique set should be 6
        unique_labels = set(data_trace.theta) - {None}
        assert unique_labels == set(_DIMENSIONS)

    def test_at_risk_fill_color(self):
        result = _make_result(rag_status="At Risk")
        fig = build_radar(result)
        data_trace = fig.data[-1]
        assert "#f39c12" in data_trace.line.color

    def test_on_track_fill_color(self):
        result = _make_result(rag_status="On Track")
        fig = build_radar(result)
        data_trace = fig.data[-1]
        assert "#2ecc71" in data_trace.line.color

    def test_critical_fill_color(self):
        result = _make_result(rag_status="Critical", composite=30)
        fig = build_radar(result)
        data_trace = fig.data[-1]
        assert "#e74c3c" in data_trace.line.color

    def test_raises_on_missing_dimension_score(self):
        """build_radar must raise ValueError when any score is None."""
        # Construct a DimensionScores with one None by bypassing Pydantic validation
        dims = DimensionScores(time=45, cost=62, scope=55, people=70, dependencies=48, risks=52)
        result = _make_result(dimensions=dims)
        # Manually corrupt one score after construction
        object.__setattr__(result.dimensions, "time", None)
        with pytest.raises(ValueError, match="Missing dimension score"):
            build_radar(result)

    def test_dark_background(self):
        fig = build_radar(MOCK_RESULT)
        assert fig.layout.paper_bgcolor == "#0d1b2a"


# ── report.py tests ──────────────────────────────────────────────────────────

class TestGenerateHtml:
    def test_contains_composite_score(self):
        html = generate_html(MOCK_RESULT, MOCK_RESULT.project_name)
        assert str(MOCK_RESULT.composite) in html

    def test_contains_rag_status(self):
        html = generate_html(MOCK_RESULT, MOCK_RESULT.project_name)
        assert MOCK_RESULT.rag_status in html

    def test_contains_project_name(self):
        html = generate_html(MOCK_RESULT, MOCK_RESULT.project_name)
        assert MOCK_RESULT.project_name in html

    def test_contains_all_dimension_scores(self):
        html = generate_html(MOCK_RESULT, MOCK_RESULT.project_name)
        dims = MOCK_RESULT.dimensions
        for score in (dims.time, dims.cost, dims.scope, dims.people, dims.dependencies, dims.risks):
            assert str(int(score)) in html

    def test_contains_executive_summary(self):
        html = generate_html(MOCK_RESULT, MOCK_RESULT.project_name)
        # Check a distinctive substring from the summary
        assert "Composite Health Score" in html

    def test_contains_recommendations(self):
        html = generate_html(MOCK_RESULT, MOCK_RESULT.project_name)
        # Check each recommendation by looking for a distinctive word sequence
        # that doesn't contain characters Jinja2 would escape
        fragments = [
            "Escalate the three open High-severity",
            "emergency milestone review",
            "single-owner overload",
        ]
        for fragment in fragments:
            assert fragment in html

    def test_raises_report_error_on_missing_rag_status(self):
        result = _make_result(rag_status="")
        with pytest.raises(ReportError, match="rag_status"):
            generate_html(result, result.project_name)

    def test_raises_report_error_on_missing_project_name(self):
        result = _make_result(project_name="")
        with pytest.raises(ReportError, match="project_name"):
            generate_html(result, result.project_name)

    def test_raises_report_error_on_missing_dimension(self):
        dims = DimensionScores(time=45, cost=62, scope=55, people=70, dependencies=48, risks=52)
        result = _make_result(dimensions=dims)
        object.__setattr__(result.dimensions, "cost", None)
        with pytest.raises(ReportError, match="dimensions.cost"):
            generate_html(result, result.project_name)

    def test_contributing_factors_shown_when_below_70(self):
        html = generate_html(MOCK_RESULT, MOCK_RESULT.project_name)
        # MOCK_RESULT composite=58 < 70, so factors section should appear
        assert "Contributing Factors" in html

    def test_contributing_factors_hidden_when_above_70(self):
        # Build a result with composite=80 and NO contributing factors
        result = _make_result(composite=80, rag_status="On Track", contributing_factors=[])
        html = generate_html(result, result.project_name)
        assert "Contributing Factors" not in html
