from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from storage.database import get_connection


@dataclass
class Todo:
    id: int
    text: str
    done: bool
    ord: float
    created_at: str
    updated_at: str


def get_all() -> list[Todo]:
    """ord 순서로 전체 반환"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM todos ORDER BY ord ASC"
        ).fetchall()
    return [_row_to_todo(r) for r in rows]


def add(text: str) -> Todo:
    """맨 끝에 추가 — ord는 현재 max + 1.0"""
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(ord) FROM todos").fetchone()
        next_ord = (row[0] or 0.0) + 1.0
        cur = conn.execute(
            "INSERT INTO todos (text, ord) VALUES (?, ?) RETURNING *",
            (text, next_ord),
        )
        return _row_to_todo(cur.fetchone())


def toggle(todo_id: int) -> Optional[Todo]:
    """done 0↔1 토글"""
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE todos
            SET done       = CASE WHEN done = 0 THEN 1 ELSE 0 END,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            RETURNING *
            """,
            (todo_id,),
        )
        row = cur.fetchone()
    return _row_to_todo(row) if row else None


def update_text(todo_id: int, text: str) -> Optional[Todo]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE todos
            SET text       = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            RETURNING *
            """,
            (text, todo_id),
        )
        row = cur.fetchone()
    return _row_to_todo(row) if row else None


def reorder(todo_id: int, new_ord: float) -> None:
    """드래그 후 새 ord 값으로 업데이트"""
    with get_connection() as conn:
        conn.execute(
            "UPDATE todos SET ord = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (new_ord, todo_id),
        )


def delete(todo_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))


def _row_to_todo(row: object) -> Todo:
    return Todo(
        id=row["id"],
        text=row["text"],
        done=bool(row["done"]),
        ord=row["ord"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )