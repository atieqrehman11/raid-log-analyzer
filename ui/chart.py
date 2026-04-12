"""Radar chart builder — no Chainlit imports."""

import plotly.graph_objects as go
from core.models import AnalysisResult

# RAG fill colours (hex)
_COLORS = {
    "On Track": "#2ecc71",
    "At Risk": "#f39c12",
    "Critical": "#e74c3c",
}


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert a #rrggbb hex string to an rgba() string accepted by Plotly."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

_DIMENSIONS = ["Time", "Cost", "Scope", "People", "Dependencies", "Risks"]
_SCORE_ATTRS = ["time", "cost", "scope", "people", "dependencies", "risks"]


def build_radar(result: AnalysisResult) -> go.Figure:
    """Return a Scatterpolar radar chart for the given AnalysisResult.

    Raises:
        ValueError: if any dimension score is None.
    """
    scores = []
    for attr in _SCORE_ATTRS:
        val = getattr(result.dimensions, attr, None)
        if val is None:
            raise ValueError("Missing dimension score")
        scores.append(val)

    fill_color = _COLORS.get(result.rag_status, "#f39c12")
    fill_rgba = _hex_to_rgba(fill_color, 0.33)

    # Close the polygon by repeating the first value
    theta = _DIMENSIONS + [_DIMENSIONS[0]]
    r_values = scores + [scores[0]]

    fig = go.Figure()

    # Explicitly set template to avoid Chainlit 2.x null template JS error
    fig.layout.template = None

    # Faint grid rings
    for level in [25, 50, 75, 100]:
        fig.add_trace(
            go.Scatterpolar(
                r=[level] * (len(_DIMENSIONS) + 1),
                theta=theta,
                mode="lines",
                line=dict(color="rgba(255,255,255,0.08)", width=1),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Main data trace
    fig.add_trace(
        go.Scatterpolar(
            r=r_values,
            theta=theta,
            fill="toself",
            fillcolor=fill_rgba,
            line=dict(color=fill_color, width=2.5),
            marker=dict(size=7, color=fill_color),
            name=result.rag_status,
            hovertemplate="%{theta}: %{r:.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(255,255,255,0.04)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(color="rgba(255,255,255,0.55)", size=10),
                gridcolor="rgba(255,255,255,0.10)",
                linecolor="rgba(255,255,255,0.10)",
                tickvals=[25, 50, 75, 100],
            ),
            angularaxis=dict(
                tickfont=dict(color="white", size=13, family="Inter, sans-serif"),
                linecolor="rgba(255,255,255,0.15)",
                gridcolor="rgba(255,255,255,0.10)",
            ),
        ),
        paper_bgcolor="#0d1b2a",
        plot_bgcolor="#0d1b2a",
        font=dict(color="white", family="Inter, sans-serif"),
        showlegend=False,
        margin=dict(l=60, r=60, t=60, b=60),
        title=dict(
            text=f"Project Health Radar — {result.rag_status}",
            font=dict(size=16, color="white"),
            x=0.5,
        ),
    )

    return fig
