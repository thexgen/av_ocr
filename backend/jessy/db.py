"""Jessy chat persistence — conversations + messages (MySQL)."""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.db.connection import DatabaseError, mysql_connection, mysql_cursor
from backend.db.settings import get_staging_defaults

logger = logging.getLogger("jessy")

_SCHEMA_READY = False


def ensure_jessy_tables() -> None:
    """Create Jessy chat tables if they do not exist."""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return

    ddl_conversations = """
    CREATE TABLE IF NOT EXISTS jessy_conversations (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        title VARCHAR(255) NOT NULL DEFAULT 'New chat',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_jessy_conv_user_updated (user_id, updated_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """
    ddl_messages = """
    CREATE TABLE IF NOT EXISTS jessy_messages (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        conversation_id BIGINT NOT NULL,
        role ENUM('user', 'assistant', 'system') NOT NULL,
        content MEDIUMTEXT NOT NULL,
        sources_json JSON NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_jessy_msg_conv (conversation_id),
        CONSTRAINT fk_jessy_msg_conv
            FOREIGN KEY (conversation_id)
            REFERENCES jessy_conversations(id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """

    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl_conversations)
                cur.execute(ddl_messages)
        _SCHEMA_READY = True
        logger.info("Jessy chat tables ready")
    except DatabaseError:
        logger.exception("Could not ensure Jessy chat tables")
        raise


def _default_user_id() -> int:
    return get_staging_defaults().user_id


def list_conversations(user_id: int | None = None) -> list[dict[str, Any]]:
    ensure_jessy_tables()
    uid = user_id if user_id is not None else _default_user_id()
    with mysql_cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, title, created_at, updated_at
            FROM jessy_conversations
            WHERE user_id = %s
            ORDER BY updated_at DESC
            """,
            (uid,),
        )
        rows = cur.fetchall() or []
    return [_serialize_conversation(row) for row in rows]


def create_conversation(
    *,
    title: str = "New chat",
    user_id: int | None = None,
) -> dict[str, Any]:
    ensure_jessy_tables()
    uid = user_id if user_id is not None else _default_user_id()
    with mysql_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO jessy_conversations (user_id, title)
                VALUES (%s, %s)
                """,
                (uid, title[:255]),
            )
            conv_id = int(cur.lastrowid)
            cur.execute(
                """
                SELECT id, user_id, title, created_at, updated_at
                FROM jessy_conversations
                WHERE id = %s
                """,
                (conv_id,),
            )
            row = cur.fetchone()
    return _serialize_conversation(row or {"id": conv_id, "user_id": uid, "title": title})


def get_conversation(conversation_id: int) -> dict[str, Any] | None:
    ensure_jessy_tables()
    with mysql_cursor() as cur:
        cur.execute(
            """
            SELECT id, user_id, title, created_at, updated_at
            FROM jessy_conversations
            WHERE id = %s
            """,
            (conversation_id,),
        )
        row = cur.fetchone()
    return _serialize_conversation(row) if row else None


def delete_conversation(conversation_id: int) -> bool:
    ensure_jessy_tables()
    with mysql_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM jessy_conversations WHERE id = %s",
                (conversation_id,),
            )
            return cur.rowcount > 0


def list_messages(conversation_id: int) -> list[dict[str, Any]]:
    ensure_jessy_tables()
    with mysql_cursor() as cur:
        cur.execute(
            """
            SELECT id, conversation_id, role, content, sources_json, created_at
            FROM jessy_messages
            WHERE conversation_id = %s
            ORDER BY id ASC
            """,
            (conversation_id,),
        )
        rows = cur.fetchall() or []
    return [_serialize_message(row) for row in rows]


def add_message(
    *,
    conversation_id: int,
    role: str,
    content: str,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    ensure_jessy_tables()
    sources_json = json.dumps(sources or [])
    with mysql_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO jessy_messages (conversation_id, role, content, sources_json)
                VALUES (%s, %s, %s, %s)
                """,
                (conversation_id, role, content, sources_json),
            )
            msg_id = int(cur.lastrowid)
            cur.execute(
                """
                UPDATE jessy_conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (conversation_id,),
            )
            cur.execute(
                """
                SELECT id, conversation_id, role, content, sources_json, created_at
                FROM jessy_messages
                WHERE id = %s
                """,
                (msg_id,),
            )
            row = cur.fetchone()
    return _serialize_message(row or {"id": msg_id, "role": role, "content": content})


def maybe_set_title_from_question(conversation_id: int, question: str) -> str | None:
    """If conversation is still 'New chat', rename from first user question.

    Returns the new title when updated, otherwise None.
    """
    title = " ".join(question.strip().split())
    if not title:
        return None
    if len(title) > 60:
        title = title[:57] + "..."

    with mysql_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE jessy_conversations
                SET title = %s
                WHERE id = %s AND title = 'New chat'
                """,
                (title, conversation_id),
            )
            if cur.rowcount > 0:
                return title
    return None


def maybe_set_ai_title(conversation_id: int, title: str) -> str | None:
    """Set AI-generated title only while the chat is still unnamed."""
    cleaned = " ".join((title or "").strip().split())
    if not cleaned:
        return None
    if len(cleaned) > 60:
        cleaned = cleaned[:57] + "..."

    with mysql_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE jessy_conversations
                SET title = %s
                WHERE id = %s AND title = 'New chat'
                """,
                (cleaned, conversation_id),
            )
            if cur.rowcount > 0:
                return cleaned
    return None


def get_conversation_title(conversation_id: int) -> str:
    conv = get_conversation(conversation_id)
    return str((conv or {}).get("title") or "New chat")


def _serialize_conversation(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "user_id": int(row.get("user_id") or 0),
        "title": str(row.get("title") or "New chat"),
        "created_at": _dt(row.get("created_at")),
        "updated_at": _dt(row.get("updated_at")),
    }


def _serialize_message(row: dict[str, Any]) -> dict[str, Any]:
    sources_raw = row.get("sources_json")
    sources: list[str] = []
    if isinstance(sources_raw, (bytes, bytearray)):
        sources_raw = sources_raw.decode("utf-8")
    if isinstance(sources_raw, str) and sources_raw:
        try:
            parsed = json.loads(sources_raw)
            if isinstance(parsed, list):
                sources = [str(x) for x in parsed]
        except json.JSONDecodeError:
            sources = []
    elif isinstance(sources_raw, list):
        sources = [str(x) for x in sources_raw]

    return {
        "id": int(row["id"]),
        "conversation_id": int(row.get("conversation_id") or 0),
        "role": str(row.get("role") or "assistant"),
        "content": str(row.get("content") or ""),
        "sources": sources,
        "created_at": _dt(row.get("created_at")),
    }


def _dt(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat(sep=" ", timespec="seconds")
    return str(value)
