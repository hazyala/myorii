from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from storage.database import get_connection


@dataclass
class ChatSession:
    id: int
    title: str
    created_at: str
    updated_at: str


@dataclass
class ChatMessage:
    id: int
    session_id: int
    role: str  # 'user' | 'assistant'
    content: str
    created_at: str


@dataclass
class ChatAttachment:
    id: int
    message_id: int
    file_path: str
    mime_type: str
    created_at: str


# ── Sessions ──────────────────────────────────────────────

def create_session(title: str = "새 대화") -> ChatSession:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO chat_sessions (title) VALUES (?) RETURNING *",
            (title,),
        )
        return _row_to_session(cur.fetchone())


def get_all_sessions() -> list[ChatSession]:
    """최신 대화 순으로 반환"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_sessions ORDER BY updated_at DESC"
        ).fetchall()
    return [_row_to_session(r) for r in rows]


def update_session_title(session_id: int, title: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE chat_sessions SET title = ? WHERE id = ?",
            (title, session_id),
        )


def touch_session(session_id: int) -> None:
    """메시지 추가될 때마다 호출 — 세션 목록 최신순 정렬용"""
    with get_connection() as conn:
        conn.execute(
            "UPDATE chat_sessions SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (session_id,),
        )


def delete_session(session_id: int) -> None:
    """CASCADE로 messages, attachments 자동 삭제"""
    with get_connection() as conn:
        conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))


# ── Messages ──────────────────────────────────────────────

def add_message(session_id: int, role: str, content: str) -> ChatMessage:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?) RETURNING *",
            (session_id, role, content),
        )
        msg = _row_to_message(cur.fetchone())

    touch_session(session_id)
    return msg


def get_messages(session_id: int) -> list[ChatMessage]:
    """세션의 전체 메시지 — LLM context 재구성용"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
    return [_row_to_message(r) for r in rows]


def get_last_n_messages(session_id: int, n: int = 20) -> list[ChatMessage]:
    """최근 N개만 — 긴 대화에서 context window 절약용"""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM (
                SELECT * FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ) ORDER BY created_at ASC
            """,
            (session_id, n),
        ).fetchall()
    return [_row_to_message(r) for r in rows]


# ── Attachments ───────────────────────────────────────────

def add_attachment(message_id: int, file_path: str, mime_type: str) -> ChatAttachment:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO chat_attachments (message_id, file_path, mime_type) VALUES (?, ?, ?) RETURNING *",
            (message_id, file_path, mime_type),
        )
        return _row_to_attachment(cur.fetchone())


def get_attachments(message_id: int) -> list[ChatAttachment]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_attachments WHERE message_id = ? ORDER BY created_at ASC",
            (message_id,),
        ).fetchall()
    return [_row_to_attachment(r) for r in rows]


# ── Helpers ───────────────────────────────────────────────

def _row_to_session(row: object) -> ChatSession:
    return ChatSession(
        id=row["id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_message(row: object) -> ChatMessage:
    return ChatMessage(
        id=row["id"],
        session_id=row["session_id"],
        role=row["role"],
        content=row["content"],
        created_at=row["created_at"],
    )


def _row_to_attachment(row: object) -> ChatAttachment:
    return ChatAttachment(
        id=row["id"],
        message_id=row["message_id"],
        file_path=row["file_path"],
        mime_type=row["mime_type"],
        created_at=row["created_at"],
    )