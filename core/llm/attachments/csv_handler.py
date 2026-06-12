from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from core.llm.attachments.context import AttachmentContext
from core.llm.contracts import ChatAttachmentPayload


class CsvHandler:
    """Summarizes csv/tsv attachments by columns and sample rows."""

    SUPPORTED_SUFFIXES = {".csv", ".tsv"}

    def __init__(self, sample_rows: int = 5, max_cell_chars: int = 120) -> None:
        self._sample_rows = sample_rows
        self._max_cell_chars = max_cell_chars

    def extract(self, attachment: ChatAttachmentPayload) -> AttachmentContext:
        path = Path(attachment.path)
        text = self._read_text(path)
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        reader = csv.reader(StringIO(text), delimiter=delimiter)
        try:
            columns = next(reader)
        except StopIteration:
            columns = []

        rows = [row for _, row in zip(range(self._sample_rows), reader)]
        body = self._format_body(columns, rows)
        return AttachmentContext(
            title=f"[첨부 표: {attachment.name}]",
            body=body,
            metadata={
                "handler": "CsvHandler",
                "mime_type": attachment.mime_type,
                "columns": columns,
                "sample_row_count": len(rows),
            },
        )

    def supports(self, attachment: ChatAttachmentPayload) -> bool:
        return Path(attachment.path).suffix.lower() in self.SUPPORTED_SUFFIXES

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise RuntimeError(f"표 파일을 읽을 수 없어요: {path.name}") from exc

    def _format_body(self, columns: list[str], rows: list[list[str]]) -> str:
        lines: list[str] = []
        if columns:
            lines.append("컬럼: " + ", ".join(column.strip() for column in columns))
        else:
            lines.append("컬럼: 없음")

        if not rows:
            lines.append("샘플 행: 없음")
            return "\n".join(lines)

        lines.append("샘플 행:")
        for index, row in enumerate(rows, start=1):
            pairs = self._row_pairs(columns, row)
            lines.append(f"{index}. " + " | ".join(pairs))
        return "\n".join(lines)

    def _row_pairs(self, columns: list[str], row: list[str]) -> list[str]:
        pairs: list[str] = []
        for index, value in enumerate(row):
            column = columns[index].strip() if index < len(columns) and columns[index].strip() else f"column_{index + 1}"
            pairs.append(f"{column}: {self._truncate_cell(value)}")
        return pairs

    def _truncate_cell(self, value: str) -> str:
        normalized = value.strip()
        if len(normalized) <= self._max_cell_chars:
            return normalized
        return normalized[: self._max_cell_chars].rstrip() + "..."
