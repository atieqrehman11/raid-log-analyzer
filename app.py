"""Chainlit entry point — Project Predictive Analyzer."""

import logging

import chainlit as cl
from core.sqlite_data_layer import SQLiteDataLayer

from mock_data import MOCK_RESULT
from ui.handlers import send_summary, send_radar_chart, send_html_report, update_thread_title

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
    """Send the welcome message when a new chat session starts."""
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
    """Handle incoming messages by running analysis and sending results."""
    result = MOCK_RESULT

    await update_thread_title(message, result.project_name)
    await send_summary(result)
    await send_radar_chart(result)
    await send_html_report(result)

    cl.user_session.set("analysis_result", result)
