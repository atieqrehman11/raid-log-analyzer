"""Message handling logic for the Chainlit UI layer."""

import logging
import os
import tempfile

import chainlit as cl
import chainlit.data as cl_data

from core.models import AnalysisResult
from ui.chart import build_radar
from ui.report import generate_html

logger = logging.getLogger(__name__)


async def update_thread_title(message: cl.Message, project_name: str) -> None:
    """Update the thread title in the data layer based on the message content."""
    data_layer = cl_data.get_data_layer()
    if data_layer:
        user = cl.context.session.user
        user_id = getattr(user, "id", None)
        title = (message.content or project_name).strip()[:60]
        await data_layer.update_thread(
            thread_id=cl.context.session.thread_id,
            name=title,
            user_id=user_id,
        )


async def send_summary(result: AnalysisResult) -> None:
    """Build and send the text summary message for the analysis result."""
    factors_text = "\n".join(
        f"  • **[{f.dimension}]** {f.label}" for f in result.contributing_factors
    )
    recs_text = "\n".join(
        f"{i + 1}. {rec}" for i, rec in enumerate(result.recommendations)
    )
    summary_text = (
        f"📊 Analysis complete for **{result.project_name}**\n\n"
        f"**Health Score:** {result.composite}/100 — {result.rag_status}\n\n"
        f"**Top Contributing Factors:**\n{factors_text}\n\n"
        f"**Summary:** {result.executive_summary}\n\n"
        f"**Recommendations:**\n{recs_text}"
    )
    await cl.Message(content=summary_text).send()


async def send_radar_chart(result: AnalysisResult) -> None:
    """Build and send the radar chart for the analysis result."""
    fig = build_radar(result)
    await cl.Message(
        content="",
        elements=[cl.Plotly(figure=fig, display="inline", size="large")],
    ).send()


async def send_html_report(result: AnalysisResult) -> None:
    """Generate and send the HTML report as a downloadable file."""
    html_content = generate_html(result, result.project_name)
    fd, tmp_path = tempfile.mkstemp(suffix=".html")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html_content)
        await cl.Message(
            content="📄 Download the full executive report:",
            elements=[
                cl.File(
                    name=f"{result.project_name.replace(' ', '_')}_health_report.html",
                    path=tmp_path,
                    mime="text/html",
                )
            ],
        ).send()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
