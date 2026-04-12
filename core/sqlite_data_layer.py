"""SQLite-compatible Chainlit data layer.

Subclasses SQLAlchemyDataLayer and patches get_all_user_threads to remove
PostgreSQL-specific NULLS LAST syntax that breaks on SQLite.
"""

import logging
from typing import Any, Dict, List, Optional

from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.types import ThreadDict

logger = logging.getLogger(__name__)

_THREAD_QUERY = """
    SELECT
        t."id"              AS thread_id,
        t."createdAt"       AS thread_createdat,
        t."name"            AS thread_name,
        t."userId"          AS user_id,
        t."userIdentifier"  AS user_identifier,
        t."tags"            AS thread_tags,
        t."metadata"        AS thread_metadata,
        MAX(s."createdAt")  AS updatedAt
    FROM threads t
    LEFT JOIN steps s ON t."id" = s."threadId"
    WHERE t."userId" = :user_id OR t."id" = :thread_id
    GROUP BY t."id", t."createdAt", t."name", t."userId",
             t."userIdentifier", t."tags", t."metadata"
    ORDER BY updatedAt DESC
    LIMIT :limit
"""

_STEPS_QUERY = """
    SELECT
        s."id"            AS step_id,
        s."name"          AS step_name,
        s."type"          AS step_type,
        s."threadId"      AS step_threadid,
        s."parentId"      AS step_parentid,
        s."streaming"     AS step_streaming,
        s."waitForAnswer" AS step_waitforanswer,
        s."isError"       AS step_iserror,
        s."metadata"      AS step_metadata,
        s."tags"          AS step_tags,
        s."input"         AS step_input,
        s."output"        AS step_output,
        s."createdAt"     AS step_createdat,
        s."command"       AS step_command,
        s."start"         AS step_start,
        s."end"           AS step_end,
        s."generation"    AS step_generation,
        s."showInput"     AS step_showinput,
        s."language"      AS step_language,
        s."indent"        AS step_indent,
        s."defaultOpen"   AS step_defaultopen,
        f."value"         AS feedback_value,
        f."comment"       AS feedback_comment,
        f."id"            AS feedback_id
    FROM steps s
    LEFT JOIN feedbacks f ON s."id" = f."forId"
    WHERE s."threadId" IN ({ids})
"""

_ELEMENTS_QUERY = """
    SELECT
        e."id"           AS element_id,
        e."threadId"     AS element_threadid,
        e."type"         AS element_type,
        e."url"          AS element_url,
        e."chainlitKey"  AS element_chainlitkey,
        e."name"         AS element_name,
        e."display"      AS element_display,
        e."objectKey"    AS element_objectkey,
        e."size"         AS element_size,
        e."page"         AS element_page,
        e."language"     AS element_language,
        e."forId"        AS element_forid,
        e."mime"         AS element_mime
    FROM elements e
    WHERE e."threadId" IN ({ids})
"""


def _ids_placeholder(rows: list) -> str:
    """Build a SQL IN clause string from a list of thread rows."""
    return "('" + "','".join(r["thread_id"] for r in rows) + "')"


def _build_thread(row: dict) -> dict:
    return {
        "id": row["thread_id"],
        "createdAt": row.get("thread_createdat") or "",
        "name": row.get("thread_name") or "",
        "userId": row.get("user_id"),
        "userIdentifier": row.get("user_identifier"),
        "tags": row.get("thread_tags"),
        "metadata": row.get("thread_metadata") or {},
        "steps": [],
        "elements": [],
    }


def _build_step(row: dict, thread_id: str) -> dict:
    step: Dict[str, Any] = {
        "id": row["step_id"],
        "name": row["step_name"],
        "type": row["step_type"],
        "threadId": thread_id,
        "parentId": row.get("step_parentid"),
        "streaming": bool(row.get("step_streaming")),
        "waitForAnswer": row.get("step_waitforanswer"),
        "isError": row.get("step_iserror"),
        "metadata": row.get("step_metadata") or {},
        "tags": row.get("step_tags"),
        "input": row.get("step_input") or "",
        "output": row.get("step_output") or "",
        "createdAt": row.get("step_createdat") or "",
        "command": row.get("step_command"),
        "start": row.get("step_start"),
        "end": row.get("step_end"),
        "generation": row.get("step_generation"),
        "showInput": row.get("step_showinput"),
        "language": row.get("step_language"),
        "indent": row.get("step_indent"),
        "defaultOpen": row.get("step_defaultopen"),
    }
    if row.get("feedback_id"):
        step["feedback"] = {
            "id": row["feedback_id"],
            "value": row["feedback_value"],
            "comment": row.get("feedback_comment"),
        }
    return step


def _build_element(row: dict, thread_id: str) -> dict:
    return {
        "id": row["element_id"],
        "threadId": thread_id,
        "type": row.get("element_type"),
        "url": row.get("element_url"),
        "chainlitKey": row.get("element_chainlitkey"),
        "name": row["element_name"],
        "display": row.get("element_display"),
        "objectKey": row.get("element_objectkey"),
        "size": row.get("element_size"),
        "page": row.get("element_page"),
        "language": row.get("element_language"),
        "forId": row.get("element_forid"),
        "mime": row.get("element_mime"),
    }


class SQLiteDataLayer(SQLAlchemyDataLayer):
    """SQLite-compatible data layer for local development."""

    async def get_all_user_threads(
        self,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> Optional[List[ThreadDict]]:
        """Return threads for a user, using SQLite-compatible ORDER BY."""
        rows = await self.execute_sql(
            query=_THREAD_QUERY,
            parameters={"user_id": user_id, "thread_id": thread_id, "limit": self.user_thread_limit},
        )
        if not isinstance(rows, list):
            return None
        if not rows:
            return []

        ids = _ids_placeholder(rows)
        thread_map = {r["thread_id"]: _build_thread(r) for r in rows}

        steps = await self.execute_sql(query=_STEPS_QUERY.format(ids=ids), parameters={})
        if isinstance(steps, list):
            for s in steps:
                tid = s.get("step_threadid")
                if tid in thread_map:
                    thread_map[tid]["steps"].append(_build_step(s, tid))

        elements = await self.execute_sql(query=_ELEMENTS_QUERY.format(ids=ids), parameters={})
        if isinstance(elements, list):
            for e in elements:
                tid = e.get("element_threadid")
                if tid in thread_map:
                    thread_map[tid]["elements"].append(_build_element(e, tid))

        return list(thread_map.values())
