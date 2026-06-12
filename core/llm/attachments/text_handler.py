from __future__ import annotations

import json
from pathlib import Path

from core.llm.attachments.context import AttachmentContext
from core.llm.contracts import ChatAttachmentPayload


class TextHandler:
    """Extracts a bounded preview from plain text-style attachments."""

    SUPPORTED_SUFFIXES = {".txt", ".md", ".json", ".yaml", ".yml"}

    def __init__(self, max_chars: int = 4000) -> None:
        self._max_chars = max_chars

    def extract(self, attachment: ChatAttachmentPayload) -> AttachmentContext:
        path = Path(attachment.path)
        text = self._read_text(path)
        if path.suffix.lower() == ".json":
            text = self._format_json(text)

        body, truncated = self._truncate(text)
        return AttachmentContext(
            title=f"[첨부 텍스트: {attachment.name}]",
            body=body,
            metadata={
                "handler": "TextHandler",
                "mime_type": attachment.mime_type,
                "truncated": truncated,
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
            raise RuntimeError(f"텍스트 파일을 읽을 수 없어요: {path.name}") from exc

    def _format_json(self, text: str) -> str:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return text
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _truncate(self, text: str) -> tuple[str, bool]:
        normalized = text.strip()
        if len(normalized) <= self._max_chars:
            return normalized, False
        return f"{normalized[:self._max_chars].rstrip()}\n\n...[내용 일부 생략]", True
