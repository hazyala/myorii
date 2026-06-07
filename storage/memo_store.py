from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from storage.database import get_connection


@dataclass
class Memo:
    id: int
    title: str
    body: str
    ord: float
    created_at: str
    updated_at: str


def get_all() -> list[Memo]:
    """ord 순서로 전체 반환"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM memos ORDER BY ord ASC"
        ).fetchall()
    return [_row_to_memo(r) for r in rows]


def add(title: str = "", body: str = "") -> Memo:
    """맨 끝에 추가"""
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(ord) FROM memos").fetchone()
        next_ord = (row[0] or 0.0) + 1.0
        cur = conn.execute(
            "INSERT INTO memos (title, body, ord) VALUES (?, ?, ?) RETURNING *",
            (title, body, next_ord),
        )
        return _row_to_memo(cur.fetchone())


def update(memo_id: int, title: str, body: str) -> Optional[Memo]:
    """제목 + 본문 동시 업데이트 — 자동저장 용도"""
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE memos
            SET title      = ?,
                body       = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            RETURNING *
            """,
            (title, body, memo_id),
        )
        row = cur.fetchone()
    return _row_to_memo(row) if row else None


def reorder(memo_id: int, new_ord: float) -> None:
    """드래그 후 새 ord 값으로 업데이트"""
    with get_connection() as conn:
        conn.execute(
            "UPDATE memos SET ord = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (new_ord, memo_id),
        )


def reorder_many(memo_ids: list[int]) -> None:
    """현재 UI 순서대로 ord를 다시 정렬"""
    with get_connection() as conn:
        conn.executemany(
            """
            UPDATE memos
            SET ord = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            """,
            [(float(index + 1), memo_id) for index, memo_id in enumerate(memo_ids)],
        )


def delete(memo_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM memos WHERE id = ?", (memo_id,))


def _row_to_memo(row: object) -> Memo:
    return Memo(
        id=row["id"],
        title=row["title"],
        body=row["body"],
        ord=row["ord"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
