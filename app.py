"""Chainlit entry point — Project Predictive Analyzer."""

import logging
import os
import tempfile

import chainlit as cl
import chainlit.data as cl_data
from core.sqlite_data_layer import SQLiteDataLayer

from mock_data import MOCK_RESULT
from ui.chart import build_radar
from ui.report import generate_html

logger = logging.getLogger(__name__)


# ── Persistent chat history via SQLite ───────────────────────────────────────
@cl.data_layer
def get_data_layer() -> SQLiteDataLayer:
    """Return the SQLite-compatible data layer for chat history."""
    return SQLiteDataLayer(conninfo="sqlite+aiosqlite:///chat_history.db")


@cl.password_auth_callback
def auth_callback(username: str, password: str) -> cl.User | None:
    """Simple local auth — any username with password 'dev' is accepted."""
    if password == "dev":
        return cl.User(identifier=username, metadata={"role": "user"})
    return None


@cl.on_chat_start
async def on_chat_start() -> None:
    await cl.Message(
        content=(
            "👋 Welcome to **Project Predictive Analyzer**.\n\n"
            "Upload your RAMID Excel workbook (.xlsx) to get started."
        )
    ).send()


@cl.on_chat_resume
async def on_chat_resume(thread: cl.types.ThreadDict) -> None:
    """Restore session context when user resumes a previous thread."""
    await cl.Message(
        content="🔄 Session resumed. You can continue asking questions or upload a new RAMID file."
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    result = MOCK_RESULT

    # ── Set thread title and link to user ─────────────────────────────────────
    data_layer = cl_data.get_data_layer()
    if data_layer:
        user = cl.context.session.user
        user_id = getattr(user, "id", None)
        title = (message.content or result.project_name).strip()[:60]
        await data_layer.update_thread(
            thread_id=cl.context.session.thread_id,
            name=title,
            user_id=user_id,
        )

    # ── 1. Text summary ───────────────────────────────────────────────────────
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

    # ── 2. Radar chart ────────────────────────────────────────────────────────
    fig = build_radar(result)
    await cl.Message(
        content="",
        elements=[cl.Plotly(figure=fig, display="inline", size="large")],
    ).send()

    # ── 3. HTML report ────────────────────────────────────────────────────────
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

    # ── Store in session for Q&A ──────────────────────────────────────────────
    cl.user_session.set("analysis_result", result)
