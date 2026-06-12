from __future__ import annotations

from core.llm.attachments.context import AttachmentContext
from core.llm.attachments.csv_handler import CsvHandler
from core.llm.attachments.text_handler import TextHandler
from core.llm.contracts import ChatAttachmentPayload


class AttachmentRouter:
    """Builds model-ready context from supported non-image attachments."""

    def __init__(
        self,
        text_handler: TextHandler | None = None,
        csv_handler: CsvHandler | None = None,
    ) -> None:
        self._csv_handler = csv_handler or CsvHandler()
        self._text_handler = text_handler or TextHandler()

    def build_contexts(self, attachments: tuple[ChatAttachmentPayload, ...]) -> tuple[AttachmentContext, ...]:
        contexts: list[AttachmentContext] = []
        for attachment in attachments:
            if attachment.is_image:
                continue
            if self._csv_handler.supports(attachment):
                contexts.append(self._csv_handler.extract(attachment))
            elif self._text_handler.supports(attachment):
                contexts.append(self._text_handler.extract(attachment))
        return tuple(contexts)
