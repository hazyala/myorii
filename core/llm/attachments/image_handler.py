from __future__ import annotations

import base64
from pathlib import Path

from core.llm.contracts import ChatAttachmentPayload


class ImageHandler:
    """Converts image attachments into Ollama-compatible base64 payloads."""

    def to_base64(self, attachment: ChatAttachmentPayload) -> str:
        path = Path(attachment.path)
        try:
            return base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError as exc:
            raise RuntimeError(f"이미지 파일을 읽을 수 없어요: {attachment.name}") from exc
